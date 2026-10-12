from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.main import create_app
from app.modules.auth.models import User
from app.modules.crm.models import Lead
from app.modules.engagement.service import on_crm_event


@pytest.fixture
def crm_client(tmp_path: Path):
    application = create_app(
        Settings(
            database_url=SecretStr(f"sqlite:///{tmp_path}/engagement.db"),
            environment="test",
        )
    )
    with TestClient(application) as client:
        response = client.post(
            "/api/v1/auth/signup",
            json={
                "name": "Test Owner",
                "company_name": "Fictional Test Company",
                "email": "owner@example.test",
                "password": "Tests-strong-pass123",
            },
        )
        assert response.status_code == 201, response.text
        yield client


def test_automation_creates_persistent_task_once_and_notification(crm_client):
    rule = crm_client.post(
        "/api/v1/automations",
        json={
            "name": "Inbound follow up",
            "trigger": "leads.created",
            "conditions": [{"field": "source", "operator": "equals", "value": "Website"}],
            "action": "create_task",
            "action_text": "Call {{name}}",
            "due_days": 1,
        },
    )
    assert rule.status_code == 201, rule.text
    lead = crm_client.post("/api/v1/leads", json={"name": "Fictional Buyer", "source": "Website"})
    assert lead.status_code == 201, lead.text
    tasks = crm_client.get("/api/v1/activities").json()["items"]
    assert len(tasks) == 1
    assert tasks[0]["name"] == "Call Fictional Buyer"
    with Session(crm_client.app.state.engine) as db:
        owner = db.scalar(select(User))
        record = db.scalar(select(Lead).where(Lead.id == lead.json()["id"]))
        on_crm_event(db, owner, "leads", record, "create")
        db.commit()
    assert len(crm_client.get("/api/v1/activities").json()["items"]) == 1
    notifications = crm_client.get("/api/v1/notifications").json()
    assert notifications["unread"] == 1
    notification_id = notifications["items"][0]["id"]
    assert crm_client.post(f"/api/v1/notifications/{notification_id}/read").status_code == 200
    assert crm_client.get("/api/v1/notifications").json()["unread"] == 0
    assert len(crm_client.get("/api/v1/automations/runs").json()["items"]) == 1


def test_rule_disabled_and_conditions_prevent_execution(crm_client):
    rule = crm_client.post(
        "/api/v1/automations",
        json={
            "name": "High value",
            "trigger": "leads.created",
            "action": "notify",
            "action_text": "New high-value buyer",
            "conditions": [{"field": "value", "operator": "gte", "value": "50000"}],
        },
    ).json()
    assert (
        crm_client.post("/api/v1/leads", json={"name": "Low value", "value": "25"}).status_code
        == 201
    )
    assert crm_client.get("/api/v1/notifications").json()["unread"] == 0
    assert (
        crm_client.patch(f"/api/v1/automations/{rule['id']}", json={"enabled": False}).status_code
        == 200
    )
    crm_client.post("/api/v1/leads", json={"name": "High value", "value": "60000"})
    assert crm_client.get("/api/v1/notifications").json()["unread"] == 0


def test_gmail_drafts_never_claim_to_send_and_tenant_scope(crm_client):
    draft = crm_client.post(
        "/api/v1/email/messages",
        json={
            "recipient": "buyer@example.test",
            "subject": "Follow up",
            "body": "Hello from tests.",
        },
    )
    assert draft.status_code == 201, draft.text
    assert draft.json()["status"] == "draft"
    draft_id = draft.json()["id"]
    response = crm_client.post(f"/api/v1/email/messages/{draft_id}/send")
    assert response.status_code == 409
    assert "not connected" in response.json()["error"]["message"]
    assert crm_client.get("/api/v1/email/messages").json()["items"][0]["status"] == "draft"
    crm_client.post(
        "/api/v1/auth/signup",
        json={
            "name": "Other Owner",
            "company_name": "Other Company",
            "email": "other@example.test",
            "password": "Other-password123",
        },
    )
    assert crm_client.get("/api/v1/email/messages").json()["items"] == []
    assert crm_client.post(f"/api/v1/email/messages/{draft_id}/send").status_code == 404


@pytest.mark.parametrize(
    "condition",
    [
        {"field": "score", "operator": "execute", "value": "anything"},
        {"field": "status", "operator": "gte", "value": "New"},
        {"field": "score", "operator": "gte", "value": "NaN"},
        {"field": "value", "operator": "gte", "value": "Infinity"},
        {"field": "amount", "operator": "gte", "value": "not a number"},
    ],
)
def test_automation_invalid_operator_rejected(crm_client, condition):
    response = crm_client.post(
        "/api/v1/automations",
        json={
            "name": "Unsafe",
            "trigger": "leads.created",
            "action_text": "Follow up",
            "conditions": [condition],
        },
    )
    assert response.status_code == 422


@pytest.mark.parametrize("entity", ["automations", "email/messages"])
def test_engagement_search_sort_pagination_and_tenant_scope(crm_client, entity):
    from app.modules.engagement.models import Automation, EmailDraft

    model = Automation if entity == "automations" else EmailDraft
    with Session(crm_client.app.state.engine) as db:
        owner = db.scalar(select(User))
        assert owner is not None
        for index in range(105):
            values = (
                {"name": f"QA {index:03}", "trigger": "leads.created", "action_text": "Follow up"}
                if entity == "automations"
                else {
                    "subject": f"QA {index:03}",
                    "recipient": "fictional@example.test",
                    "body": "Saved draft",
                }
            )
            db.add(model(org_id=owner.org_id, owner_id=owner.id, **values))
        db.commit()
    first = crm_client.get(f"/api/v1/{entity}?q=QA&sort=name&order=asc&limit=20&offset=0")
    last = crm_client.get(f"/api/v1/{entity}?q=QA&sort=name&order=asc&limit=20&offset=100")
    assert first.status_code == last.status_code == 200
    assert first.json()["total"] == last.json()["total"] == 105
    assert len(first.json()["items"]) == 20
    assert len(last.json()["items"]) == 5
    assert last.json()["page"] == 6
    field = "name" if entity == "automations" else "subject"
    assert first.json()["items"][0][field] == "QA 000"
    assert last.json()["items"][-1][field] == "QA 104"
    descending = crm_client.get(f"/api/v1/{entity}?q=QA&sort=name&order=desc&limit=1").json()
    assert descending["items"][0][field] == "QA 104"
    assert crm_client.get(f"/api/v1/{entity}?q=QA%20001").json()["total"] == 1
    assert crm_client.get(f"/api/v1/{entity}?q=%25").json()["total"] == 0
    assert crm_client.get(f"/api/v1/{entity}?sort=unsupported").status_code == 422
    assert crm_client.get(f"/api/v1/{entity}?limit=0").status_code == 422
    signup = crm_client.post(
        "/api/v1/auth/signup",
        json={
            "name": "QA other owner",
            "company_name": "QA other tenant",
            "email": "other@example.test",
            "password": "Disposable-qa-123!",
        },
    )
    assert signup.status_code == 201
    assert crm_client.get(f"/api/v1/{entity}?q=QA").json()["total"] == 0


def test_paginated_email_search_only_counts_current_reps_drafts(crm_client):
    crm_client.post(
        "/api/v1/email/messages",
        json={
            "recipient": "buyer@example.test",
            "subject": "QA private owner",
            "body": "Private draft",
        },
    )
    member = crm_client.post(
        "/api/v1/team",
        json={
            "name": "QA Rep",
            "email": "rep@example.test",
            "password": "Disposable-rep-123!",
            "role": "Sales Rep",
        },
    )
    assert member.status_code == 201
    assert (
        crm_client.post(
            "/api/v1/auth/login",
            json={
                "email": "rep@example.test",
                "password": "Disposable-rep-123!",
            },
        ).status_code
        == 200
    )
    assert crm_client.get("/api/v1/email/messages?q=QA&limit=1").json()["total"] == 0
    created = crm_client.post(
        "/api/v1/email/messages",
        json={
            "recipient": "buyer@example.test",
            "subject": "QA rep draft",
            "body": "Own draft",
        },
    )
    assert created.status_code == 201
    result = crm_client.get("/api/v1/email/messages?q=QA&sort=name&order=asc&limit=1").json()
    assert result["total"] == 1
    assert result["items"][0]["id"] == created.json()["id"]
