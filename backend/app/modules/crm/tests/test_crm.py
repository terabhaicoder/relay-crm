from collections.abc import Iterator
from pathlib import Path
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.main import create_app
from app.modules.crm.models import Contact, Deal, Party


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    app = create_app(
        Settings(
            database_url=SecretStr(f"sqlite:///{tmp_path}/crm.db"),
            environment="test",
            upload_dir=tmp_path / "uploads",
        )
    )
    with TestClient(app) as http:
        response = http.post(
            "/api/v1/auth/signup",
            json={
                "name": "Aditi",
                "email": "owner@example.com",
                "password": "Test-pass-234!",
                "company_name": "Company",
            },
        )
        assert response.status_code == 201, response.text
        yield http


def make(client: TestClient, entity: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = client.post(f"/api/v1/{entity}", json=payload)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


def test_conversion_atomic_and_idempotent_and_ledger_values_decimal(client: TestClient) -> None:
    lead = make(
        client,
        "leads",
        {"name": "Priya", "company": "Acme", "phone": "9876543210", "value": "1234.56"},
    )
    assert lead["phone"] == "+919876543210"
    assert lead["value"] == "1234.56"
    result = client.post(f"/api/v1/leads/{lead['id']}/convert", json={})
    assert result.status_code == 200, result.text
    assert result.json()["deal"]["amount"] == "1234.56"
    repeated = client.post(f"/api/v1/leads/{lead['id']}/convert", json={})
    assert repeated.status_code == 200
    assert repeated.json()["already_converted"] is True
    assert repeated.json()["contact"]["id"] == result.json()["contact"]["id"]
    with Session(cast(Any, client.app).state.engine) as db:
        assert db.scalar(select(func.count()).select_from(Contact)) == 1
        assert db.scalar(select(func.count()).select_from(Party)) == 1
        assert db.scalar(select(func.count()).select_from(Deal)) == 1
    assert client.patch(f"/api/v1/leads/{lead['id']}", json={"name": "Changed"}).status_code == 409


def test_stage_history_lost_reason_and_closed_pipeline(client: TestClient) -> None:
    deal = make(client, "deals", {"name": "New business", "amount": "10000.00"})
    assert client.get("/api/v1/dashboard").json()["pipeline_value"] == "10000.00"
    assert client.post(f"/api/v1/deals/{deal['id']}/lost", json={}).status_code == 422
    response = client.post(f"/api/v1/deals/{deal['id']}/lost", json={"reason": "Budget"})
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "lost"
    assert len(client.get(f"/api/v1/deals/{deal['id']}/history").json()["items"]) == 2
    assert client.get("/api/v1/dashboard").json()["pipeline_value"] == "0.00"
    assert len(client.get(f"/api/v1/deals/{deal['id']}/timeline").json()["items"]) == 2


def test_other_org_records_are_hidden_and_relationships_blocked(client: TestClient) -> None:
    party = make(client, "parties", {"name": "Private account"})
    lead = make(client, "leads", {"name": "Private lead"})
    client.post(
        "/api/v1/auth/signup",
        json={
            "name": "Other",
            "company_name": "Other",
            "email": "other@example.com",
            "password": "Test-pass-234!",
        },
    )
    assert client.get(f"/api/v1/leads/{lead['id']}").status_code == 404
    assert client.patch(f"/api/v1/leads/{lead['id']}", json={"name": "Hack"}).status_code == 404
    assert (
        client.post(
            "/api/v1/contacts", json={"name": "Attempt", "party_id": party["id"]}
        ).status_code
        == 404
    )
    assert client.get("/api/v1/leads").json()["total"] == 0
    assert client.get("/api/v1/search?q=Private").json()["items"] == []


def test_import_partial_rows_and_server_search(client: TestClient) -> None:
    data = "name,email,phone\n" + "\n".join(
        f"Lead {i},person{i}@example.com,{'wrong' if i % 50 == 0 else '9876543210'}"
        for i in range(1000)
    )
    response = client.post("/api/v1/leads/import", json={"csv": data, "mode": "create"})
    assert response.status_code == 200, response.text
    assert response.json()["created"] == 980
    assert response.json()["failed"] == 20
    assert "Phone" in response.json()["error_csv"] or "phone" in response.json()["error_csv"]
    listing = client.get("/api/v1/leads?limit=10&offset=10")
    assert listing.json()["total"] == 980
    assert len(listing.json()["items"]) == 10
    assert client.get("/api/v1/leads?q=Lead%20101").json()["total"] == 1
    assert len(client.get("/api/v1/leads/export").text.splitlines()) == 981


def test_idempotent_create_version_conflict_and_validation(client: TestClient) -> None:
    headers = {"Idempotency-Key": "test-key"}
    a = client.post("/api/v1/leads", json={"name": "Same"}, headers=headers)
    b = client.post("/api/v1/leads", json={"name": "Same"}, headers=headers)
    assert a.status_code == b.status_code == 201
    assert a.json()["id"] == b.json()["id"]
    assert (
        client.post("/api/v1/leads", json={"name": "Changed"}, headers=headers).status_code == 409
    )
    record = a.json()
    assert (
        client.patch(
            f"/api/v1/leads/{record['id']}", json={"name": "Updated", "version": 1}
        ).status_code
        == 200
    )
    assert (
        client.patch(
            f"/api/v1/leads/{record['id']}", json={"name": "Stale", "version": 1}
        ).status_code
        == 409
    )
    assert (
        client.post("/api/v1/leads", json={"name": "Invalid", "email": "invalid"}).status_code
        == 422
    )
    assert (
        client.post("/api/v1/deals", json={"name": "Invalid", "amount": "0.001"}).status_code == 422
    )


def test_ticket_internal_note_reply_draft_and_resolution(client: TestClient) -> None:
    account = make(client, "parties", {"name": "Support account"})
    ticket = make(
        client, "tickets", {"name": "Cannot sign in", "party_id": account["id"], "priority": "high"}
    )
    internal = client.post(
        f"/api/v1/tickets/{ticket['id']}/messages", json={"body": "Investigating", "internal": True}
    )
    reply = client.post(
        f"/api/v1/tickets/{ticket['id']}/messages",
        json={"body": "We are checking", "internal": False},
    )
    assert internal.json()["delivery_status"] == "internal"
    assert reply.json()["delivery_status"] == "draft"
    assert client.patch(f"/api/v1/tickets/{ticket['id']}", json={"status": "Resolved"}).json()[
        "resolved_at"
    ]
    assert client.get("/api/v1/dashboard").json()["open_tickets"] == 0


def test_demo_seed_is_opt_in_idempotent_and_real(client: TestClient) -> None:
    assert client.get("/api/v1/demo/status").json()["seeded"] is False
    result = client.post("/api/v1/demo/seed")
    assert result.status_code == 200, result.text
    before = client.get("/api/v1/dashboard").json()
    assert before["counts"]["leads"] == 8
    assert before["counts"]["deals"] == 7
    assert before["open_deals"] == 5
    assert client.post("/api/v1/demo/seed").json()["already_seeded"] is True
    after = client.get("/api/v1/dashboard").json()
    assert before["counts"] == after["counts"]
    assert client.get("/api/v1/demo/status").json()["seeded"] is True


def test_failed_conversion_rolls_back_account_and_contact(client: TestClient) -> None:
    party = make(client, "parties", {"name": "Existing"})
    contact = make(client, "contacts", {"name": "Existing person", "party_id": party["id"]})
    other = make(client, "parties", {"name": "Different company"})
    lead = make(client, "leads", {"name": "Unconverted", "company": "Should rollback"})
    response = client.post(
        f"/api/v1/leads/{lead['id']}/convert",
        json={"contact_id": contact["id"], "party_id": other["id"]},
    )
    assert response.status_code == 422, response.text
    assert client.get("/api/v1/parties").json()["total"] == 2
    assert client.get("/api/v1/contacts").json()["total"] == 1
    assert client.get("/api/v1/deals").json()["total"] == 0
    assert client.get(f"/api/v1/leads/{lead['id']}").json()["status"] == "New"


def test_export_import_preserves_phone_and_formula_name(client: TestClient) -> None:
    make(client, "leads", {"name": '=HYPERLINK("bad")', "phone": "+919876543210"})
    exported = client.get("/api/v1/leads/export").text
    assert "'+919876543210" in exported
    response = client.post("/api/v1/leads/import", json={"csv": exported, "mode": "update"})
    assert response.status_code == 200, response.text
    assert response.json()["updated"] == 1
    assert response.json()["failed"] == 0


def test_read_only_cannot_write_or_seed(client: TestClient) -> None:
    from app.modules.auth.models import User

    lead = make(client, "leads", {"name": "Read only record"})
    with Session(cast(Any, client.app).state.engine) as db:
        user = db.scalar(select(User))
        assert user is not None
        user.role = "Read-only"
        db.commit()
    assert client.get("/api/v1/leads").status_code == 200
    assert client.post("/api/v1/leads", json={"name": "Blocked"}).status_code == 403
    assert client.patch(f"/api/v1/leads/{lead['id']}", json={"name": "Blocked"}).status_code == 403
    assert client.post("/api/v1/demo/seed").status_code == 403


def test_concurrent_idempotency_creates_only_one_record(client: TestClient) -> None:
    from concurrent.futures import ThreadPoolExecutor

    def submit() -> Any:
        return client.post(
            "/api/v1/leads",
            json={"name": "Concurrent"},
            headers={"Idempotency-Key": "concurrent-1"},
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: submit(), range(2)))
    assert [result.status_code for result in results] == [201, 201]
    assert results[0].json()["id"] == results[1].json()["id"]
    assert client.get("/api/v1/leads").json()["total"] == 1


def test_won_automation_fires_only_on_transition(client: TestClient) -> None:
    automation = client.post(
        "/api/v1/automations",
        json={
            "name": "Welcome won customer",
            "trigger": "deals.won",
            "action": "create_task",
            "action_text": "Onboard {{name}}",
        },
    )
    assert automation.status_code == 201, automation.text
    deal = make(client, "deals", {"name": "New account"})
    assert client.post(f"/api/v1/deals/{deal['id']}/won").status_code == 200
    assert client.get("/api/v1/activities").json()["total"] == 1
    assert (
        client.patch(f"/api/v1/deals/{deal['id']}", json={"notes": "Updated after win"}).status_code
        == 200
    )
    assert client.post(f"/api/v1/deals/{deal['id']}/won").status_code == 200
    assert client.get("/api/v1/activities").json()["total"] == 1


def test_dashboard_filters_created_record_cohort(client: TestClient) -> None:
    from datetime import timedelta

    from app.modules.crm.models import Lead, now

    old = make(client, "leads", {"name": "Old cohort"})
    make(client, "leads", {"name": "Current cohort"})
    with Session(cast(Any, client.app).state.engine) as db:
        lead = db.get(Lead, old["id"])
        assert lead is not None
        lead.created_at = now() - timedelta(days=60)
        db.commit()
    assert client.get("/api/v1/dashboard").json()["counts"]["leads"] == 2
    filtered = client.get("/api/v1/dashboard?period=30d").json()
    assert filtered["counts"]["leads"] == 1
    assert filtered["period_basis"] == "records_created"
    assert client.get("/api/v1/dashboard?period=invalid").status_code == 422


def test_sales_rep_own_scope_applies_to_lists_search_dashboard_and_export(
    client: TestClient,
) -> None:
    from app.modules.auth.models import User

    own = make(client, "leads", {"name": "Own lead"})
    with Session(cast(Any, client.app).state.engine) as db:
        owner = db.scalar(select(User))
        assert owner is not None
        colleague = User(
            org_id=owner.org_id,
            name="Colleague",
            email="colleague@example.com",
            password_hash="not-a-login-hash",
            role="Sales Rep",
        )
        db.add(colleague)
        db.flush()
        colleague_id = colleague.id
        db.commit()
    other = make(client, "leads", {"name": "Colleague lead", "owner_id": colleague_id})
    with Session(cast(Any, client.app).state.engine) as db:
        current = db.scalar(select(User).where(User.email == "owner@example.com"))
        assert current is not None
        current.role = "Sales Rep"
        db.commit()
    assert client.get("/api/v1/leads").json()["total"] == 1
    assert client.get(f"/api/v1/leads/{own['id']}").status_code == 200
    assert client.get(f"/api/v1/leads/{other['id']}").status_code == 404
    assert client.get("/api/v1/search?q=Colleague").json()["items"] == []
    assert client.get("/api/v1/dashboard").json()["counts"]["leads"] == 1
    assert "Colleague lead" not in client.get("/api/v1/leads/export").text
    assert (
        client.post(
            "/api/v1/leads", json={"name": "Assign away", "owner_id": colleague_id}
        ).status_code
        == 403
    )


def test_lead_merge_keeps_target_moves_activities_and_preserves_history(client: TestClient) -> None:
    target = make(
        client,
        "leads",
        {
            "name": "Keep this lead",
            "email": "keep@example.com",
            "tags": ["priority"],
            "notes": "Target note",
        },
    )
    source = make(
        client,
        "leads",
        {
            "name": "Duplicate lead",
            "email": "source@example.com",
            "phone": "9876543210",
            "tags": ["referral"],
            "notes": "Source note",
        },
    )
    activity = make(
        client,
        "activities",
        {"name": "Follow up", "entity_type": "leads", "entity_id": source["id"]},
    )
    response = client.post(
        f"/api/v1/leads/{source['id']}/merge",
        json={"target_id": target["id"], "source_version": 1, "target_version": 1},
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["lead"]["id"] == target["id"]
    assert result["lead"]["email"] == "keep@example.com"
    assert result["lead"]["phone"] == "+919876543210"
    assert result["lead"]["tags"] == ["priority", "referral"]
    assert "Source note" in result["lead"]["notes"]
    assert result["moved_activities"] == 1
    assert client.get("/api/v1/leads").json()["total"] == 1
    assert client.get(f"/api/v1/leads/{source['id']}").status_code == 404
    assert client.get(f"/api/v1/activities/{activity['id']}").json()["entity_id"] == target["id"]
    timeline = client.get(f"/api/v1/leads/{target['id']}/timeline").json()["items"]
    assert any(
        event["entity_id"] == source["id"] and event["action"] == "created" for event in timeline
    )
    repeat = client.post(
        "/api/v1/leads/merge", json={"source_id": source["id"], "target_id": target["id"]}
    )
    assert repeat.status_code == 200, repeat.text
    assert repeat.json()["already_merged"] is True
    assert client.get("/api/v1/activities").json()["total"] == 1
    assert len(client.get(f"/api/v1/leads/{target['id']}/timeline").json()["items"]) == len(
        timeline
    )


def test_lead_merge_validation_rolls_back_and_converted_blocked(client: TestClient) -> None:
    target = make(client, "leads", {"name": "Target", "tags": [f"target{i}" for i in range(20)]})
    source = make(client, "leads", {"name": "Source", "tags": [f"source{i}" for i in range(20)]})
    activity = make(
        client,
        "activities",
        {"name": "Do not move", "entity_type": "leads", "entity_id": source["id"]},
    )
    rejected = client.post(f"/api/v1/leads/{source['id']}/merge", json={"target_id": target["id"]})
    assert rejected.status_code == 422
    assert client.get(f"/api/v1/leads/{source['id']}").json()["version"] == 1
    assert client.get(f"/api/v1/activities/{activity['id']}").json()["entity_id"] == source["id"]
    assert client.get(f"/api/v1/leads/{target['id']}").json()["tags"] == target["tags"]
    assert (
        client.post(
            f"/api/v1/leads/{source['id']}/merge", json={"target_id": source["id"]}
        ).status_code
        == 422
    )
    assert client.post(f"/api/v1/leads/{source['id']}/convert", json={}).status_code == 200
    assert (
        client.post(
            f"/api/v1/leads/{source['id']}/merge", json={"target_id": target["id"]}
        ).status_code
        == 409
    )


def test_lead_merge_cross_org_and_stale_version_denied(client: TestClient) -> None:
    source = make(client, "leads", {"name": "Source"})
    target = make(client, "leads", {"name": "Target"})
    assert (
        client.post(
            f"/api/v1/leads/{source['id']}/merge",
            json={"target_id": target["id"], "target_version": 99},
        ).status_code
        == 409
    )
    client.post(
        "/api/v1/auth/signup",
        json={
            "name": "Other",
            "company_name": "Other",
            "email": "othermerge@example.com",
            "password": "Test-pass-234!",
        },
    )
    other = make(client, "leads", {"name": "Other org target"})
    response = client.post(f"/api/v1/leads/{source['id']}/merge", json={"target_id": other["id"]})
    assert response.status_code == 404
    assert client.get("/api/v1/leads").json()["total"] == 1


def test_lead_merge_retains_attachment_download_and_email_draft(client: TestClient) -> None:
    source = make(client, "leads", {"name": "Source with files"})
    target = make(client, "leads", {"name": "Keep account prospect"})
    upload = client.post(
        f"/api/v1/attachments?entity_type=leads&entity_id={source['id']}&filename=meeting.txt",
        content=b"Important meeting notes",
        headers={"Content-Type": "text/plain"},
    )
    assert upload.status_code == 201, upload.text
    draft = client.post(
        "/api/v1/email/messages",
        json={
            "recipient": "person@example.com",
            "subject": "Follow-up",
            "body": "Thank you",
            "entity_type": "leads",
            "entity_id": source["id"],
        },
    )
    assert draft.status_code == 201, draft.text
    merged = client.post(f"/api/v1/leads/{source['id']}/merge", json={"target_id": target["id"]})
    assert merged.status_code == 200, merged.text
    attachments = client.get(
        f"/api/v1/attachments?entity_type=leads&entity_id={target['id']}"
    ).json()["items"]
    assert len(attachments) == 1
    assert attachments[0]["id"] == upload.json()["id"]
    download = client.get(f"/api/v1/attachments/{upload.json()['id']}/download")
    assert download.status_code == 200
    assert download.content == b"Important meeting notes"
    messages = client.get("/api/v1/email/messages").json()["items"]
    assert (
        next(message for message in messages if message["id"] == draft.json()["id"])["entity_id"]
        == target["id"]
    )


def test_duplicate_lookup_normalizes_phone_and_tolerates_incomplete_input(
    client: TestClient,
) -> None:
    lead = make(client, "leads", {"name": "Same person", "phone": "9876543210"})
    response = client.get("/api/v1/leads/duplicates", params={"phone": "+919876543210"})
    assert response.status_code == 200
    assert response.json()["items"][0]["id"] == lead["id"]
    partial = client.get("/api/v1/leads/duplicates", params={"phone": "9876"})
    assert partial.status_code == 200
    assert partial.json()["validation_pending"] is True


def test_nullable_and_blank_deal_relations_return_validation_not_server_errors(
    client: TestClient,
) -> None:
    deal = make(client, "deals", {"name": "Stable stage"})
    for field in ["stage_id", "pipeline_id"]:
        for invalid in [None, ""]:
            result = client.patch(f"/api/v1/deals/{deal['id']}", json={field: invalid})
            assert result.status_code == 422, result.text
    contact = make(client, "contacts", {"name": "Optional company", "party_id": ""})
    assert contact["party_id"] is None
    assert client.get(f"/api/v1/deals/{deal['id']}").json()["stage_id"] == deal["stage_id"]


def test_conversion_reuses_existing_contact_company_and_links_unassigned_contact(
    client: TestClient,
) -> None:
    company = make(client, "parties", {"name": "Existing customer"})
    contact = make(client, "contacts", {"name": "Person", "party_id": company["id"]})
    lead = make(client, "leads", {"name": "Person enquiry"})
    result = client.post(f"/api/v1/leads/{lead['id']}/convert", json={"contact_id": contact["id"]})
    assert result.status_code == 200, result.text
    assert result.json()["party"]["id"] == company["id"]
    assert client.get("/api/v1/parties").json()["total"] == 1
    unassigned = make(client, "contacts", {"name": "Unassigned"})
    second = make(client, "leads", {"name": "Unassigned enquiry"})
    result = client.post(
        f"/api/v1/leads/{second['id']}/convert",
        json={"contact_id": unassigned["id"], "party_id": company["id"]},
    )
    assert result.status_code == 200, result.text
    assert client.get(f"/api/v1/contacts/{unassigned['id']}").json()["party_id"] == company["id"]


def test_archive_guards_linked_records_and_preserves_version_on_failure(client: TestClient) -> None:
    company = make(client, "parties", {"name": "Account"})
    contact = make(client, "contacts", {"name": "Linked contact", "party_id": company["id"]})
    assert client.delete(f"/api/v1/parties/{company['id']}").status_code == 409
    assert client.get(f"/api/v1/parties/{company['id']}").json()["version"] == 1
    assert client.delete(f"/api/v1/contacts/{contact['id']}").status_code == 204
    assert client.delete(f"/api/v1/parties/{company['id']}").status_code == 204
    lead = make(client, "leads", {"name": "Lead with task"})
    activity = make(
        client, "activities", {"name": "Task", "entity_type": "leads", "entity_id": lead["id"]}
    )
    assert client.delete(f"/api/v1/leads/{lead['id']}").status_code == 409
    assert (
        client.patch(
            f"/api/v1/activities/{activity['id']}", json={"entity_id": None, "entity_type": None}
        ).status_code
        == 200
    )
    assert client.delete(f"/api/v1/leads/{lead['id']}").status_code == 204


def test_terminal_status_timestamps_do_not_change_on_repeat_save(client: TestClient) -> None:
    ticket = make(client, "tickets", {"name": "Already resolved", "status": "Resolved"})
    changed = client.patch(f"/api/v1/tickets/{ticket['id']}", json={"status": "Closed"}).json()
    assert changed["resolved_at"] == ticket["resolved_at"]
    assert (
        client.patch(f"/api/v1/tickets/{ticket['id']}", json={"status": "Open"}).json()[
            "resolved_at"
        ]
        is None
    )
    task = make(client, "activities", {"name": "Already done", "status": "completed"})
    assert (
        client.post(f"/api/v1/activities/{task['id']}/complete").json()["completed_at"]
        == task["completed_at"]
    )


def test_contact_and_company_mismatch_rejected_for_deals_and_tickets(client: TestClient) -> None:
    first = make(client, "parties", {"name": "First"})
    second = make(client, "parties", {"name": "Second"})
    contact = make(client, "contacts", {"name": "First contact", "party_id": first["id"]})
    for entity in ["deals", "tickets"]:
        result = client.post(
            f"/api/v1/{entity}",
            json={"name": "Mismatched", "party_id": second["id"], "contact_id": contact["id"]},
        )
        assert result.status_code == 422, result.text
        assert client.get(f"/api/v1/{entity}").json()["total"] == 0


def test_sqlite_money_limit_and_decimal_dashboard_totals(client: TestClient) -> None:
    from decimal import Decimal

    maximum = "999999999999.99"
    expected = Decimal("0")
    for index in range(12):
        deal = make(client, "deals", {"name": f"Exact {index}", "amount": maximum})
        assert client.get(f"/api/v1/deals/{deal['id']}").json()["amount"] == maximum
        expected += Decimal(maximum)
    dashboard = client.get("/api/v1/dashboard").json()
    assert dashboard["pipeline_value"] == str(expected)
    assert dashboard["weighted_pipeline"] == str(
        (expected / Decimal("10")).quantize(Decimal("0.01"))
    )
    for entity, field in [
        ("deals", "amount"),
        ("leads", "value"),
        ("campaigns", "budget"),
        ("campaigns", "spent"),
    ]:
        rejected = client.post(
            f"/api/v1/{entity}", json={"name": "Too large", field: "1000000000000.00"}
        )
        assert rejected.status_code == 422, rejected.text


def test_date_normalization_rejects_ambiguous_inputs(client: TestClient) -> None:
    result = make(
        client, "activities", {"name": "Timed call", "due_date": "2026-10-12T15:30:00+05:30"}
    )
    assert result["due_date"] == "2026-10-12T10:00:00+00:00"
    for invalid in ["20261012", "not-a-date", "2026-10-12T15:30:00"]:
        assert (
            client.post(
                "/api/v1/activities", json={"name": "Invalid", "due_date": invalid}
            ).status_code
            == 422
        )


def test_ticket_message_retry_is_idempotent_and_blank_body_rejected(client: TestClient) -> None:
    ticket = make(client, "tickets", {"name": "Conversation"})
    endpoint = f"/api/v1/tickets/{ticket['id']}/messages"
    headers = {"Idempotency-Key": "same-note"}
    first = client.post(endpoint, json={"body": "A real note"}, headers=headers)
    second = client.post(endpoint, json={"body": "A real note"}, headers=headers)
    assert first.status_code == second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    assert len(client.get(endpoint).json()["items"]) == 1
    assert client.post(endpoint, json={"body": "   "}).status_code == 422


def test_concurrent_first_pipeline_reads_create_one_default(client: TestClient) -> None:
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(lambda _: client.get("/api/v1/pipelines"), range(2)))
    assert [response.status_code for response in responses] == [200, 200]
    pipeline_sets = [response.json()["items"] for response in responses]
    assert len(pipeline_sets[0]) == len(pipeline_sets[1]) == 1
    assert pipeline_sets[0][0]["id"] == pipeline_sets[1][0]["id"]
    assert len(pipeline_sets[0][0]["stages"]) == 6


def test_import_savepoints_remain_inside_outer_transaction(client: TestClient) -> None:
    from app.modules.auth.models import User
    from app.modules.crm.service import import_csv

    with Session(cast(Any, client.app).state.engine) as db:
        user = db.scalar(select(User))
        assert user is not None
        result = import_csv(
            db, user, "leads", "name,email\nRollback row,row@example.com\n", "create"
        )
        assert result["created"] == 1
        db.rollback()
    assert client.get("/api/v1/leads").json()["total"] == 0


def test_dashboard_history_and_cached_conversion_respect_current_ownership(
    client: TestClient,
) -> None:
    from app.modules.auth.models import User

    lead = make(client, "leads", {"name": "Private old record"})
    headers = {"Idempotency-Key": "convert-once"}
    converted = client.post(f"/api/v1/leads/{lead['id']}/convert", json={}, headers=headers).json()
    with Session(cast(Any, client.app).state.engine) as db:
        current = db.scalar(select(User))
        assert current is not None
        colleague = User(
            org_id=current.org_id,
            name="Other owner",
            email="owner2@example.com",
            password_hash="not-login",
            role="Sales Rep",
        )
        db.add(colleague)
        db.flush()
        contact = db.get(Contact, converted["contact"]["id"])
        assert contact is not None
        contact.owner_id = colleague.id
        current.role = "Sales Rep"
        db.commit()
    result = client.get("/api/v1/dashboard").json()
    assert all(
        event["entity_id"] != converted["contact"]["id"] for event in result["recent_activity"]
    )
    replay = client.post(f"/api/v1/leads/{lead['id']}/convert", json={}, headers=headers)
    assert replay.status_code == 404
