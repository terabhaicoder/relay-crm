"""Cross-module regression cases found by the comprehensive CRM audit."""

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
    app = create_app(
        Settings(
            environment="test",
            database_url=SecretStr(f"sqlite:///{tmp_path}/connected.db"),
            upload_dir=tmp_path / "uploads",
        )
    )
    with TestClient(app) as http:
        make(
            http,
            "auth/signup",
            name="Audit owner",
            email="owner@audit.test",
            password="Audit-password-234!",
            company_name="Disposable audit",
        )
        yield http


def make(client: TestClient, entity: str, **payload: Any) -> dict[str, Any]:
    response = client.post(f"/api/v1/{entity}", json=payload)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


def login_rep(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "rep@audit.test", "password": "Audit-password-234!"},
    )
    assert response.status_code == 200, response.text


def make_rep(client: TestClient) -> dict[str, Any]:
    return make(
        client,
        "team",
        name="Audit rep",
        email="rep@audit.test",
        password="Audit-password-234!",
        role="Sales Rep",
    )


def test_assigned_work_can_progress_without_granting_customer_access(client: TestClient) -> None:
    rep = make_rep(client)
    company = make(client, "parties", name="Owner account")
    contact = make(client, "contacts", name="Owner contact", party_id=company["id"])
    deal = make(
        client,
        "deals",
        name="Assigned deal",
        owner_id=rep["id"],
        party_id=company["id"],
        contact_id=contact["id"],
    )
    ticket = make(
        client,
        "tickets",
        name="Assigned support",
        owner_id=rep["id"],
        party_id=company["id"],
        contact_id=contact["id"],
        deal_id=deal["id"],
    )
    lead = make(client, "leads", name="Owner lead")
    other = make(client, "leads", name="Other private lead")
    task = make(
        client,
        "activities",
        name="Assigned task",
        owner_id=rep["id"],
        entity_type="leads",
        entity_id=lead["id"],
    )
    login_rep(client)
    assert client.post(f"/api/v1/deals/{deal['id']}/won").status_code == 200
    assert client.post(f"/api/v1/activities/{task['id']}/complete").status_code == 200
    assert (
        client.patch(f"/api/v1/tickets/{ticket['id']}", json={"status": "Resolved"}).status_code
        == 200
    )
    for entity, record in (("parties", company), ("contacts", contact), ("leads", lead)):
        assert client.get(f"/api/v1/{entity}/{record['id']}").status_code == 404
        assert client.get(f"/api/v1/{entity}/{record['id']}/timeline").status_code == 404
        assert client.get(f"/api/v1/{entity}").json()["total"] == 0
    assert client.get("/api/v1/search?q=Owner").json()["items"] == []
    denied = client.patch(f"/api/v1/activities/{task['id']}", json={"entity_id": other["id"]})
    assert denied.status_code == 404
    assert client.get(f"/api/v1/activities/{task['id']}").json()["entity_id"] == lead["id"]
    assert (
        client.post(
            "/api/v1/activities",
            json={"name": "Unauthorized new link", "entity_type": "leads", "entity_id": lead["id"]},
        ).status_code
        == 404
    )
    # A retained entity ID is not permission to change the polymorphic type.
    assert (
        client.patch(
            f"/api/v1/activities/{task['id']}", json={"entity_type": "contacts"}
        ).status_code
        == 404
    )


def test_pipeline_probability_updates_forecast_versions_and_audit(client: TestClient) -> None:
    rep = make_rep(client)
    deal = make(client, "deals", name="Existing opportunity", owner_id=rep["id"], amount="10000.00")
    won = make(client, "deals", name="Closed opportunity", amount="2500.00")
    assert client.post(f"/api/v1/deals/{won['id']}/won").status_code == 200
    pipeline = client.get("/api/v1/pipelines").json()["items"][0]
    stages = [
        {key: stage[key] for key in ("id", "name", "probability", "category")}
        for stage in pipeline["stages"]
    ]
    next(stage for stage in stages if stage["id"] == deal["stage_id"])["probability"] = 90
    response = client.patch(f"/api/v1/pipelines/{pipeline['id']}", json={"stages": stages})
    assert response.status_code == 200, response.text
    stored = client.get(f"/api/v1/deals/{deal['id']}").json()
    assert stored["probability"] == 90
    assert stored["version"] == deal["version"] + 1
    assert client.get("/api/v1/dashboard").json()["weighted_pipeline"] == "9000.00"
    assert client.get(f"/api/v1/deals/{won['id']}").json()["probability"] == 100
    timeline = client.get(f"/api/v1/deals/{deal['id']}/timeline").json()["items"]
    assert any(event["changes"].get("probability") == {"old": 10, "new": 90} for event in timeline)
    assert len(client.get(f"/api/v1/deals/{deal['id']}/history").json()["items"]) == 1
    stale = client.patch(
        f"/api/v1/deals/{deal['id']}", json={"version": deal["version"], "name": "Old editor"}
    )
    assert stale.status_code == 409
    # Editing stage labels/order must not silently reset an API-level deal override.
    assert client.patch(f"/api/v1/deals/{deal['id']}", json={"probability": 50}).status_code == 200
    stages[0]["name"] = "Renamed discovery"
    assert (
        client.patch(f"/api/v1/pipelines/{pipeline['id']}", json={"stages": stages}).status_code
        == 200
    )
    assert client.get(f"/api/v1/deals/{deal['id']}").json()["probability"] == 50


def test_draft_edit_preserves_omitted_links_and_validates_final_pair(client: TestClient) -> None:
    lead = make(client, "leads", name="Draft recipient")
    draft = make(
        client,
        "email/messages",
        recipient="buyer@audit.test",
        subject="Original",
        body="Original body",
        entity_type="leads",
        entity_id=lead["id"],
    )
    body = {"recipient": "buyer@audit.test", "subject": "Updated", "body": "Updated body"}
    response = client.patch(f"/api/v1/email/messages/{draft['id']}", json=body)
    assert response.status_code == 200, response.text
    assert response.json()["entity_id"] == lead["id"]
    stored = client.get(f"/api/v1/email/messages/{draft['id']}")
    assert stored.status_code == 200
    assert stored.json()["entity_type"] == "leads"
    assert stored.json()["subject"] == "Updated"
    incomplete = client.patch(
        f"/api/v1/email/messages/{draft['id']}", json={**body, "entity_type": None}
    )
    assert incomplete.status_code == 422
    unlinked = client.patch(
        f"/api/v1/email/messages/{draft['id']}",
        json={**body, "entity_type": None, "entity_id": None},
    )
    assert unlinked.status_code == 200
    assert unlinked.json()["entity_id"] is None


def test_draft_get_enforces_owner_and_tenant_scope(client: TestClient) -> None:
    make_rep(client)
    draft = make(
        client, "email/messages", recipient="buyer@audit.test", subject="Private", body="Private"
    )
    login_rep(client)
    assert client.get(f"/api/v1/email/messages/{draft['id']}").status_code == 404
    own = make(client, "email/messages", recipient="buyer@audit.test", subject="Own", body="Own")
    assert client.get(f"/api/v1/email/messages/{own['id']}").status_code == 200
    make(
        client,
        "auth/signup",
        name="Other owner",
        email="other@audit.test",
        password="Audit-password-234!",
        company_name="Another tenant",
    )
    for record in (draft, own):
        assert client.get(f"/api/v1/email/messages/{record['id']}").status_code == 404


def test_draft_record_filter_is_paginated_and_checks_parent_access(client: TestClient) -> None:
    rep = make_rep(client)
    lead = make(client, "leads", name="Shared assignment", owner_id=rep["id"])
    private = make(client, "leads", name="Private parent")
    make(
        client,
        "email/messages",
        recipient="buyer@audit.test",
        subject="Owner draft on rep record",
        body="Private draft content",
        entity_type="leads",
        entity_id=lead["id"],
    )
    login_rep(client)
    for index in range(3):
        make(
            client,
            "email/messages",
            recipient="buyer@audit.test",
            subject=f"Linked {index}",
            body="Linked content",
            entity_type="leads",
            entity_id=lead["id"],
        )
    make(client, "email/messages", recipient="buyer@audit.test", subject="Unrelated", body="Body")
    path = f"/api/v1/email/messages?entity_type=leads&entity_id={lead['id']}"
    response = client.get(path + "&limit=1&offset=1&sort=name&order=asc")
    assert response.status_code == 200, response.text
    assert response.json()["total"] == 3
    assert [row["subject"] for row in response.json()["items"]] == ["Linked 1"]
    assert client.get(path + "&q=Linked%202").json()["total"] == 1
    assert client.get("/api/v1/email/messages?entity_type=leads").status_code == 422
    assert client.get(f"/api/v1/email/messages?entity_id={lead['id']}").status_code == 422
    assert (
        client.get(
            f"/api/v1/email/messages?entity_type=leads&entity_id={private['id']}"
        ).status_code
        == 404
    )
    make(
        client,
        "auth/signup",
        name="Foreign owner",
        email="foreign@audit.test",
        password="Audit-password-234!",
        company_name="Foreign tenant",
    )
    assert client.get(path).status_code == 404
