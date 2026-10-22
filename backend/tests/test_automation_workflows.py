"""Real SQLite/API tests for durable, permission-aware local workflow execution."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from typing import Any, cast

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.db import build_local_engine
from app.modules.auth.models import User, utcnow
from app.modules.crm import service as crm_service
from app.modules.crm.models import Activity, AuditEvent, Lead
from app.modules.crm.tests.test_crm import client as crm_client
from app.modules.crm.tests.test_crm import make
from app.modules.engagement.models import AutomationJob, AutomationRun, Notification
from app.modules.engagement.workflows import process_due_jobs

client = crm_client


def factory(client: TestClient) -> sessionmaker[Session]:
    return sessionmaker(bind=cast(Any, client.app).state.engine, expire_on_commit=False)


def step(action: str = "create_task", **values: Any) -> dict[str, Any]:
    return {"action": action, "action_text": "Follow up {{name}}", "delay_minutes": 0, **values}


def rule(client: TestClient, **values: Any) -> dict[str, Any]:
    return make(
        client,
        "automations",
        {
            "name": "Durable follow-up",
            "trigger": "leads.created",
            "steps": [step()],
            **values,
        },
    )


def jobs(client: TestClient, suffix: str = "") -> list[dict[str, Any]]:
    return sorted(
        client.get("/api/v1/automations/jobs" + suffix).json()["items"],
        key=lambda row: row["step_index"],
    )


def test_delayed_chain_preserves_snapshot_and_connects_task_assignment_notification(
    client: TestClient,
) -> None:
    rep = make(
        client,
        "team",
        {
            "name": "Workflow rep",
            "email": "rep@workflow.test",
            "password": "Workflow-pass-123",
            "role": "Sales Rep",
        },
    )
    original = {
        "name": "Original process",
        "trigger": "leads.created",
        "conditions": [{"field": "source", "operator": "equals", "value": "Website"}],
        "steps": [
            step(action_text="Original {{name}}"),
            step("assign_owner", owner_id=rep["id"], delay_minutes=5),
            step("notify", action_text="Assigned {{name}}", delay_minutes=2),
        ],
    }
    saved = rule(client, **original)
    lead = make(client, "leads", {"name": "Buyer", "source": "Website"})
    assert client.get("/api/v1/activities").json()["total"] == 0
    before = jobs(client)
    assert len(before) == 3 and before[1]["scheduled_at"] is None
    assert (
        client.patch(
            f"/api/v1/automations/{saved['id']}",
            json={
                **original,
                "name": "Edited rule",
                "steps": [step(action_text="New rule text")],
                "conditions": [{"field": "source", "operator": "equals", "value": "Referral"}],
            },
        ).status_code
        == 200
    )
    at = utcnow() + timedelta(seconds=1)
    assert process_due_jobs(factory(client), at=at)["completed"] == 1
    task = client.get("/api/v1/activities").json()["items"][0]
    assert task["name"] == "Original Buyer"
    assert (task["entity_type"], task["entity_id"]) == ("leads", lead["id"])
    assert process_due_jobs(factory(client), at=at + timedelta(minutes=4))["processed"] == 0
    assert process_due_jobs(factory(client), at=at + timedelta(minutes=5))["completed"] == 1
    assert client.get(f"/api/v1/leads/{lead['id']}").json()["owner_id"] == rep["id"]
    assert process_due_jobs(factory(client), at=at + timedelta(minutes=7))["completed"] == 1
    completed = jobs(client)
    assert all(row["status"] == "completed" and row["attempts"] == 1 for row in completed)
    assert all(row["rule_name"] == "Original process" for row in completed)
    assert completed[0]["result_entity_id"] == task["id"]
    assert client.get("/api/v1/automations/runs").json()["items"][0]["status"] == "completed"
    with factory(client)() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(Notification)
                .where(Notification.user_id == rep["id"])
            )
            == 1
        )


def test_condition_recheck_skips_chain_without_partial_actions(client: TestClient) -> None:
    rule(
        client,
        conditions=[{"field": "status", "operator": "equals", "value": "New"}],
        steps=[step(delay_minutes=5), step("notify")],
    )
    lead = make(client, "leads", {"name": "Changed buyer"})
    assert (
        client.patch(f"/api/v1/leads/{lead['id']}", json={"status": "Qualified"}).status_code == 200
    )
    result = process_due_jobs(factory(client), at=utcnow() + timedelta(minutes=6))
    assert result["skipped"] == 1
    assert all(row["status"] == "skipped" for row in jobs(client))
    assert client.get("/api/v1/activities").json()["total"] == 0
    assert client.get("/api/v1/notifications").json()["unread"] == 0


def test_pause_cancels_pending_steps_and_resume_does_not_resurrect(client: TestClient) -> None:
    saved = rule(client, steps=[step(), step("notify", delay_minutes=10)])
    make(client, "leads", {"name": "Paused buyer"})
    assert process_due_jobs(factory(client), at=utcnow() + timedelta(seconds=1))["completed"] == 1
    assert (
        client.patch(f"/api/v1/automations/{saved['id']}", json={"enabled": False}).status_code
        == 200
    )
    assert [row["status"] for row in jobs(client)] == ["completed", "cancelled"]
    assert client.get("/api/v1/automations?enabled=false").json()["total"] == 1
    assert (
        client.patch(f"/api/v1/automations/{saved['id']}", json={"enabled": True}).status_code
        == 200
    )
    assert process_due_jobs(factory(client), at=utcnow() + timedelta(days=1))["processed"] == 0


def test_inactive_target_fails_then_manager_retry_is_once(client: TestClient) -> None:
    rep = make(
        client,
        "team",
        {
            "name": "Target rep",
            "email": "target@workflow.test",
            "password": "Workflow-pass-123",
            "role": "Sales Rep",
        },
    )
    rule(client, steps=[step(owner_id=rep["id"])])
    make(client, "leads", {"name": "Retry buyer"})
    assert client.patch(f"/api/v1/team/{rep['id']}", json={"is_active": False}).status_code == 200
    assert process_due_jobs(factory(client), at=utcnow() + timedelta(seconds=1))["failed"] == 1
    failed = jobs(client)[0]
    assert "teammate" in failed["error_detail"]
    assert failed["attempts"] == 1
    assert client.get("/api/v1/activities").json()["total"] == 0
    assert client.patch(f"/api/v1/team/{rep['id']}", json={"is_active": True}).status_code == 200
    assert client.post(f"/api/v1/automations/jobs/{failed['id']}/retry").status_code == 200
    assert client.post(f"/api/v1/automations/jobs/{failed['id']}/retry").status_code == 409
    assert process_due_jobs(factory(client), at=utcnow() + timedelta(seconds=1))["completed"] == 1
    assert process_due_jobs(factory(client), at=utcnow() + timedelta(days=1))["processed"] == 0
    assert jobs(client)[0]["attempts"] == 2
    assert client.get("/api/v1/activities").json()["total"] == 1


def test_actor_permission_is_revalidated_and_manager_can_cancel(client: TestClient) -> None:
    admin = make(
        client,
        "team",
        {
            "name": "Rule admin",
            "email": "admin@workflow.test",
            "password": "Workflow-pass-123",
            "role": "Admin",
        },
    )
    owner_token = client.cookies.get("erp_session")
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"email": "admin@workflow.test", "password": "Workflow-pass-123"},
        ).status_code
        == 200
    )
    rule(client)
    client.cookies.clear()
    client.cookies.set("erp_session", owner_token)
    make(client, "leads", {"name": "Owner buyer"})
    assert (
        client.patch(f"/api/v1/team/{admin['id']}", json={"role": "Sales Rep"}).status_code == 200
    )
    assert process_due_jobs(factory(client), at=utcnow() + timedelta(seconds=1))["failed"] == 1
    failed = jobs(client)[0]
    assert "manager" in failed["error_detail"]
    assert client.post(f"/api/v1/automations/jobs/{failed['id']}/retry").status_code == 403
    assert client.post(f"/api/v1/automations/jobs/{failed['id']}/cancel").status_code == 200
    assert client.get("/api/v1/automations/runs").json()["items"][0]["status"] == "cancelled"


def test_action_failure_rolls_back_generated_task_and_audit_before_retry(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    rule(client)
    make(client, "leads", {"name": "Atomic buyer"})
    original = crm_service.create

    def fail_after_create(*args: Any, **kwargs: Any) -> Any:
        original(*args, **kwargs)
        raise HTTPException(422, "Injected validation after CRM write")

    monkeypatch.setattr(crm_service, "create", fail_after_create)
    assert process_due_jobs(factory(client), at=utcnow() + timedelta(seconds=1))["failed"] == 1
    with factory(client)() as db:
        assert db.scalar(select(func.count()).select_from(Activity)) == 0
        assert (
            db.scalar(
                select(func.count())
                .select_from(AuditEvent)
                .where(AuditEvent.entity_type == "activities")
            )
            == 0
        )
        assert db.scalar(select(func.count()).select_from(Notification)) == 0
    monkeypatch.setattr(crm_service, "create", original)
    assert client.post(f"/api/v1/automations/jobs/{jobs(client)[0]['id']}/retry").status_code == 200
    assert process_due_jobs(factory(client), at=utcnow() + timedelta(seconds=1))["completed"] == 1
    assert client.get("/api/v1/activities").json()["total"] == 1


def test_queue_rolls_back_with_originating_transaction(client: TestClient) -> None:
    rule(client)
    with factory(client)() as db:
        owner = db.scalar(select(User))
        assert owner
        crm_service.create(db, owner, "leads", {"name": "Rolled back"})
        assert db.scalar(select(func.count()).select_from(AutomationJob)) == 1
        db.rollback()
    with factory(client)() as db:
        for model in (Lead, AutomationRun, AutomationJob):
            assert db.scalar(select(func.count()).select_from(model)) == 0


def test_concurrent_workers_and_event_retry_do_not_duplicate_or_recurse(client: TestClient) -> None:
    rule(client)
    rule(client, name="Activity listener", trigger="activities.created")
    with ThreadPoolExecutor(max_workers=2) as pool:
        created = list(
            pool.map(
                lambda _: client.post(
                    "/api/v1/leads",
                    json={"name": "Concurrent buyer"},
                    headers={"Idempotency-Key": "lead-once"},
                ),
                range(2),
            )
        )
    assert [response.status_code for response in created] == [201, 201]
    assert len(jobs(client)) == 1
    at = utcnow() + timedelta(seconds=1)
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: process_due_jobs(factory(client), at=at), range(2)))
    assert sum(outcome["completed"] for outcome in outcomes) == 1
    assert client.get("/api/v1/activities").json()["total"] == 1
    assert len(jobs(client)) == 1
    assert client.get("/api/v1/automations/runs").json()["total"] == 1


def test_persistent_jobs_survive_new_engine_and_history_filters(client: TestClient) -> None:
    saved = rule(client, name="Persistent process", steps=[step(), step("notify")])
    lead = make(client, "leads", {"name": "Persistent buyer"})
    engine = build_local_engine(cast(Any, client.app).state.settings)
    try:
        assert (
            process_due_jobs(sessionmaker(bind=engine), at=utcnow() + timedelta(seconds=1))[
                "completed"
            ]
            == 2
        )
    finally:
        engine.dispose()
    response = client.get(
        f"/api/v1/automations/jobs?rule_id={saved['id']}&status=completed&q=Persistent&entity_type=leads&entity_id={lead['id']}&limit=1&offset=1"
    )
    assert response.status_code == 200
    assert response.json()["total"] == 2 and len(response.json()["items"]) == 1
    assert response.json()["items"][0]["trigger"] == "leads.created"
    assert client.get("/api/v1/automations/jobs?status=unknown").status_code == 422
    assert client.get("/api/v1/automations/jobs?entity_id=unknown").status_code == 422


def test_history_owner_tenant_and_manager_action_permissions(client: TestClient) -> None:
    rep = make(
        client,
        "team",
        {
            "name": "Visible rep",
            "email": "visible@workflow.test",
            "password": "Workflow-pass-123",
            "role": "Sales Rep",
        },
    )
    saved = rule(client, steps=[step(delay_minutes=5)])
    make(client, "leads", {"name": "Private buyer"})
    make(client, "leads", {"name": "Rep buyer", "owner_id": rep["id"]})
    private_job = next(row for row in jobs(client) if row["entity_name"] == "Private buyer")
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"email": "visible@workflow.test", "password": "Workflow-pass-123"},
        ).status_code
        == 200
    )
    visible = jobs(client)
    assert len(visible) == 1 and visible[0]["entity_name"] == "Rep buyer"
    assert client.post(f"/api/v1/automations/jobs/{visible[0]['id']}/retry").status_code == 403
    assert client.post(f"/api/v1/automations/jobs/{visible[0]['id']}/cancel").status_code == 403
    make(
        client,
        "auth/signup",
        {
            "name": "Other",
            "email": "other@workflow.test",
            "password": "Workflow-pass-123",
            "company_name": "Other",
        },
    )
    assert client.get("/api/v1/automations/jobs").json()["total"] == 0
    assert client.get(f"/api/v1/automations/jobs?rule_id={saved['id']}").status_code == 404
    assert client.post(f"/api/v1/automations/jobs/{private_job['id']}/cancel").status_code == 404
    foreign_target = client.post(
        "/api/v1/automations",
        json={
            "name": "Invalid target",
            "trigger": "leads.created",
            "steps": [step("assign_owner", owner_id=rep["id"])],
        },
    )
    assert foreign_target.status_code == 404


def test_delayed_work_follows_merged_lead_and_keeps_snapshot(client: TestClient) -> None:
    target = make(client, "leads", {"name": "Retained buyer"})
    rule(client, steps=[step(delay_minutes=5)])
    source = make(client, "leads", {"name": "Duplicate buyer"})
    before = jobs(client)[0]
    with factory(client)() as db:
        stored = db.get(AutomationJob, before["id"])
        assert stored
        snapshot = stored.snapshot
    merged = client.post(f"/api/v1/leads/{source['id']}/merge", json={"target_id": target["id"]})
    assert merged.status_code == 200, merged.text
    assert process_due_jobs(factory(client), at=utcnow() + timedelta(minutes=6))["completed"] == 1
    task = client.get("/api/v1/activities").json()["items"][0]
    assert task["entity_id"] == target["id"]
    assert task["name"] == "Follow up Retained buyer"
    with factory(client)() as db:
        stored = db.get(AutomationJob, before["id"])
        assert stored and stored.snapshot == snapshot
        assert stored.entity_id == target["id"]


def test_archived_source_failed_work_can_still_be_cancelled(client: TestClient) -> None:
    rule(client, steps=[step(delay_minutes=5)])
    lead = make(client, "leads", {"name": "Archived buyer"})
    assert client.delete(f"/api/v1/leads/{lead['id']}").status_code == 204
    assert process_due_jobs(factory(client), at=utcnow() + timedelta(minutes=6))["failed"] == 1
    failed = jobs(client)[0]
    assert client.post(f"/api/v1/automations/jobs/{failed['id']}/cancel").status_code == 200
    assert jobs(client)[0]["status"] == "cancelled"


@pytest.mark.parametrize(
    "steps",
    [
        [step("assign_owner", owner_id=None)],
        [step(action_text="")],
        [step(delay_minutes=-1)],
        [step()] * 9,
        [step(delay_minutes=30000), step(delay_minutes=30000)],
    ],
)
def test_workflow_validation_is_bounded(client: TestClient, steps: list[dict[str, Any]]) -> None:
    response = client.post(
        "/api/v1/automations",
        json={"name": "Invalid workflow", "trigger": "leads.created", "steps": steps},
    )
    assert response.status_code == 422
