"""Regression checks from the complete CRM audit; all records use temporary SQLite."""

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    application = create_app(
        Settings(database_url=SecretStr(f"sqlite:///{tmp_path}/integrity.db"), environment="test")
    )
    with TestClient(application) as http:
        response = http.post(
            "/api/v1/auth/signup",
            json={
                "name": "QA Owner",
                "company_name": "Disposable QA",
                "email": "qa@example.test",
                "password": "Disposable-qa-123!",
            },
        )
        assert response.status_code == 201
        yield http


def make(client: TestClient, entity: str, **payload: Any) -> dict[str, Any]:
    response = client.post(f"/api/v1/{entity}", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.parametrize("linked", [False, True])
def test_automation_activity_followup_can_be_edited_and_completed(
    client: TestClient, linked: bool
) -> None:
    make(
        client,
        "automations",
        name="Follow up completed task",
        trigger="activities.completed",
        action="create_task",
        action_text="Follow up {{name}}",
    )
    relationship = {}
    if linked:
        lead = make(client, "leads", name="QA Buyer")
        relationship = {"entity_type": "leads", "entity_id": lead["id"]}
    source = make(client, "activities", name="QA Call", **relationship)
    assert client.post(f"/api/v1/activities/{source['id']}/complete").status_code == 200
    tasks = client.get("/api/v1/activities").json()["items"]
    followup = next(task for task in tasks if task["id"] != source["id"])
    response = client.patch(f"/api/v1/activities/{followup['id']}", json={"name": "QA Follow-up"})
    assert response.status_code == 200, response.text
    assert response.json()["entity_type"] == relationship.get("entity_type")
    assert response.json()["entity_id"] == relationship.get("entity_id")
    assert client.post(f"/api/v1/activities/{followup['id']}/complete").status_code == 200


def test_ticket_rejects_contact_from_another_deals_company_without_explicit_company(
    client: TestClient,
) -> None:
    first = make(client, "parties", name="QA Company A")
    other = make(client, "parties", name="QA Company B")
    contact = make(client, "contacts", name="QA Contact B", party_id=other["id"])
    deal = make(client, "deals", name="QA Deal A", party_id=first["id"])
    response = client.post(
        "/api/v1/tickets",
        json={
            "name": "QA inconsistent support request",
            "deal_id": deal["id"],
            "contact_id": contact["id"],
        },
    )
    assert response.status_code == 422, response.text
    assert client.get("/api/v1/tickets").json()["total"] == 0


def test_contact_company_change_cannot_invalidate_linked_deal(client: TestClient) -> None:
    first = make(client, "parties", name="QA Company A")
    other = make(client, "parties", name="QA Company B")
    contact = make(client, "contacts", name="QA Contact", party_id=first["id"])
    make(client, "deals", name="QA Deal", party_id=first["id"], contact_id=contact["id"])
    response = client.patch(f"/api/v1/contacts/{contact['id']}", json={"party_id": other["id"]})
    assert response.status_code == 409, response.text
    stored = client.get(f"/api/v1/contacts/{contact['id']}").json()
    assert stored["party_id"] == first["id"]
    assert stored["version"] == contact["version"]


def test_sales_rep_cannot_clear_owner_and_lose_own_record(client: TestClient) -> None:
    make(
        client,
        "team",
        name="QA Rep",
        email="rep@example.test",
        password="Disposable-rep-123!",
        role="Sales Rep",
    )
    assert (
        client.post(
            "/api/v1/auth/login",
            json={
                "email": "rep@example.test",
                "password": "Disposable-rep-123!",
            },
        ).status_code
        == 200
    )
    lead = make(client, "leads", name="QA assigned lead")
    response = client.patch(f"/api/v1/leads/{lead['id']}", json={"owner_id": None})
    assert response.status_code == 403, response.text
    assert client.get(f"/api/v1/leads/{lead['id']}").status_code == 200


@pytest.mark.parametrize("edited", ["contacts", "deals"])
def test_company_change_checks_ticket_relationships_without_explicit_company(
    client: TestClient,
    edited: str,
) -> None:
    first = make(client, "parties", name="QA Company A")
    other = make(client, "parties", name="QA Company B")
    contact = make(client, "contacts", name="QA Contact", party_id=first["id"])
    deal = make(client, "deals", name="QA Deal", party_id=first["id"])
    make(client, "tickets", name="QA Ticket", contact_id=contact["id"], deal_id=deal["id"])
    record = contact if edited == "contacts" else deal
    response = client.patch(f"/api/v1/{edited}/{record['id']}", json={"party_id": other["id"]})
    assert response.status_code == 409, response.text
    assert client.get(f"/api/v1/{edited}/{record['id']}").json()["party_id"] == first["id"]


@pytest.mark.parametrize(
    "role", ["Admin", "Sales Manager", "Sales Rep", "Support Agent", "Read-only"]
)
def test_implemented_role_permissions_are_enforced_by_api(client: TestClient, role: str) -> None:
    lead = make(client, "leads", name="QA owner's lead")
    ticket = make(client, "tickets", name="QA owner's ticket")
    make(
        client,
        "team",
        name="QA Member",
        email="member@example.test",
        password="Disposable-member-123!",
        role=role,
    )
    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "member@example.test",
            "password": "Disposable-member-123!",
        },
    )
    assert login.status_code == 200
    expected = 404 if role == "Sales Rep" else 200
    assert client.get(f"/api/v1/leads/{lead['id']}").status_code == expected
    assert client.get(f"/api/v1/tickets/{ticket['id']}").status_code == expected
    created = client.post("/api/v1/leads", json={"name": "QA member's lead"})
    assert created.status_code == (403 if role == "Read-only" else 201)
    rule = client.post(
        "/api/v1/automations",
        json={
            "name": "QA rule",
            "trigger": "leads.created",
            "action_text": "QA follow up",
        },
    )
    assert rule.status_code == (201 if role in {"Admin", "Sales Manager"} else 403)
    invitation = client.post("/api/v1/team/invites", json={"email": "fictional@example.test"})
    assert invitation.status_code == (201 if role == "Admin" else 403)
    if role == "Read-only":
        for method, url, payload in [
            ("patch", f"/api/v1/leads/{lead['id']}", {"name": "No"}),
            ("delete", f"/api/v1/leads/{lead['id']}", None),
            ("post", f"/api/v1/leads/{lead['id']}/convert", {}),
            ("post", f"/api/v1/tickets/{ticket['id']}/messages", {"body": "No"}),
        ]:
            assert client.request(method, url, json=payload).status_code == 403


def test_legacy_automation_followup_repairs_link_when_completed(client: TestClient) -> None:
    from sqlalchemy.orm import Session

    from app.modules.crm.models import Activity

    lead = make(client, "leads", name="QA legacy context")
    source = make(client, "activities", name="QA source", entity_type="leads", entity_id=lead["id"])
    followup = make(client, "activities", name="QA old generated followup")
    with Session(client.app.state.engine) as db:
        record = db.get(Activity, followup["id"])
        assert record is not None
        record.entity_type, record.entity_id = "activities", source["id"]
        db.commit()
    edited = client.patch(
        f"/api/v1/activities/{followup['id']}",
        json={"name": "QA repaired", "entity_type": "activities", "entity_id": source["id"]},
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["entity_type"] == "leads"
    response = client.post(f"/api/v1/activities/{followup['id']}/complete")
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "completed"
    assert response.json()["entity_type"] == "leads"
    assert response.json()["entity_id"] == lead["id"]
    stored = client.get(f"/api/v1/activities/{followup['id']}").json()
    assert stored["entity_id"] == lead["id"]
