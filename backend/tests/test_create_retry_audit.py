"""Create retry regression checks against real isolated SQLite transactions."""

from concurrent.futures import ThreadPoolExecutor
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.auth.models import User
from app.modules.crm.models import Lead
from app.modules.crm.tests.test_crm import client as crm_client

client = crm_client


@pytest.mark.parametrize(
    ("entity", "payload"),
    [
        (
            "automations",
            {"name": "QA rule", "trigger": "leads.created", "action_text": "QA follow up"},
        ),
        (
            "email/messages",
            {"recipient": "qa@example.test", "subject": "QA draft", "body": "Unsent"},
        ),
        ("email/templates", {"name": "QA template", "subject": "QA greeting", "body": "Template"}),
        ("pipelines", {"name": "QA pipeline", "stages": ["QA discovery", "QA qualified"]}),
    ],
)
def test_create_retry_concurrent_conflict_permissions_and_tenant(
    client: TestClient,
    entity: str,
    payload: dict[str, Any],
) -> None:
    headers = {"Idempotency-Key": "qa-create-retry"}

    def submit() -> Any:
        return client.post(f"/api/v1/{entity}", json=payload, headers=headers)

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: submit(), range(2)))
    assert [response.status_code for response in responses] == [201, 201], [
        r.text for r in responses
    ]
    first_id = responses[0].json()["id"]
    assert responses[1].json()["id"] == first_id
    assert submit().json()["id"] == first_id
    assert len(client.get(f"/api/v1/{entity}").json()["items"]) == 1
    changed = {**payload, "subject" if entity == "email/messages" else "name": "QA changed"}
    assert client.post(f"/api/v1/{entity}", json=changed, headers=headers).status_code == 409
    with Session(cast(Any, client.app).state.engine) as db:
        owner = db.scalar(select(User))
        assert owner is not None
        owner.role = "Read-only"
        db.commit()
    assert submit().status_code == 403
    signup = client.post(
        "/api/v1/auth/signup",
        json={
            "name": "QA Other",
            "company_name": "QA Other tenant",
            "email": "other@example.test",
            "password": "Disposable-qa-123!",
        },
    )
    assert signup.status_code == 201
    other = submit()
    assert other.status_code == 201
    assert other.json()["id"] != first_id
    assert len(client.get(f"/api/v1/{entity}").json()["items"]) == 1


def test_draft_retry_rechecks_current_link_access(client: TestClient) -> None:
    lead = client.post("/api/v1/leads", json={"name": "QA private parent"}).json()
    body = {
        "recipient": "qa@example.test",
        "subject": "QA linked draft",
        "body": "Unsent",
        "entity_type": "leads",
        "entity_id": lead["id"],
    }
    headers = {"Idempotency-Key": "qa-draft-retry"}
    first = client.post("/api/v1/email/messages", json=body, headers=headers)
    assert first.status_code == 201
    with Session(cast(Any, client.app).state.engine) as db:
        owner = db.scalar(select(User))
        assert owner is not None
        owner.role = "Sales Rep"
        record = db.get(Lead, lead["id"])
        assert record is not None
        record.owner_id = None
        db.commit()
    assert client.post("/api/v1/email/messages", json=body, headers=headers).status_code == 404


@pytest.mark.parametrize("entity", ["email/messages", "email/templates"])
def test_deleted_cached_create_is_not_replayed(client: TestClient, entity: str) -> None:
    payload = {"subject": "QA deleted", "body": "Unsent"}
    payload.update(
        {"recipient": "qa@example.test"} if entity == "email/messages" else {"name": "QA template"}
    )
    headers = {"Idempotency-Key": "qa-deleted-create"}
    first = client.post(f"/api/v1/{entity}", json=payload, headers=headers)
    assert first.status_code == 201
    assert client.delete(f"/api/v1/{entity}/{first.json()['id']}").status_code == 204
    assert client.post(f"/api/v1/{entity}", json=payload, headers=headers).status_code == 404
