from concurrent.futures import ThreadPoolExecutor
from typing import Any, cast
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.auth.models import User
from app.modules.crm.models import Activity, Lead
from app.modules.crm.tests.test_crm import client as crm_client
from app.modules.crm.tests.test_crm import make
from app.modules.intake.models import CaptureSubmission

client = crm_client


def form(client: TestClient, **overrides: Any) -> dict[str, Any]:
    result = client.post(
        "/api/v1/capture-forms",
        headers={"Idempotency-Key": str(uuid4())},
        json={
            "name": "Website inquiries",
            "title": "Tell us what you need",
            **overrides,
        },
    )
    assert result.status_code == 201, result.text
    return cast(dict[str, Any], result.json())


def submit(client: TestClient, form_id: str, key: str | None = None, **overrides: Any) -> Any:
    return client.post(
        f"/api/v1/public/forms/{form_id}",
        headers={"Idempotency-Key": key or str(uuid4())},
        json={
            "name": "A customer",
            "email": "customer@example.test",
            "phone": "9876543210",
            "company": "Northstar",
            "message": "Please contact me",
            "consent": True,
            **overrides,
        },
    )


def test_public_capture_persists_and_triggers_crm_followup(client: TestClient) -> None:
    make(
        client,
        "automations",
        {
            "name": "Follow up",
            "trigger": "leads.created",
            "action": "create_task",
            "action_text": "Call inquiry",
            "due_days": 1,
        },
    )
    capture = form(client)
    client.cookies.clear()
    details = client.get(f"/api/v1/public/forms/{capture['id']}")
    assert details.status_code == 200
    assert set(details.json()) == {"id", "title", "description", "organization"}
    response = submit(client, capture["id"], "same-key")
    assert response.status_code == 201, response.text
    assert set(response.json()) == {"accepted", "message"}
    assert submit(client, capture["id"], "same-key").json() == response.json()
    assert submit(client, capture["id"], "same-key", message="changed").status_code == 409
    with Session(cast(Any, client.app).state.engine) as db:
        lead = db.scalar(select(Lead))
        assert lead and lead.email == "customer@example.test" and lead.phone == "+919876543210"
        task = db.scalar(select(Activity))
        assert task and task.entity_id == lead.id and task.name == "Call inquiry"
        assert db.scalar(select(func.count()).select_from(CaptureSubmission)) == 1


def test_round_robin_duplicate_retains_owner_and_validation(client: TestClient) -> None:
    first = make(
        client,
        "team",
        {
            "name": "Rep One",
            "email": "one@example.test",
            "password": "Secure-password123!",
            "role": "Sales Rep",
        },
    )
    second = make(
        client,
        "team",
        {
            "name": "Rep Two",
            "email": "two@example.test",
            "password": "Secure-password123!",
            "role": "Sales Rep",
        },
    )
    capture = form(client, owner_ids=[first["id"], second["id"]])
    assert submit(client, capture["id"], email="bad").status_code == 422
    assert submit(client, capture["id"], consent=False).status_code == 422
    assert submit(client, capture["id"]).status_code == 201
    assert submit(client, capture["id"], message="Second inquiry").status_code == 201
    assert submit(client, capture["id"], email="another@example.test", phone="").status_code == 201
    leads = client.get("/api/v1/leads").json()["items"]
    assert len(leads) == 2
    assert {lead["email"]: lead["owner_id"] for lead in leads} == {
        "customer@example.test": first["id"],
        "another@example.test": second["id"],
    }
    config = client.get("/api/v1/capture-forms").json()["items"][0]
    assert (config["submissions"], config["new_leads"], config["duplicates"]) == (3, 2, 1)
    receipts = client.get(
        f"/api/v1/capture-forms/{capture['id']}/submissions?limit=1&offset=1"
    ).json()
    assert receipts["total"] == 3 and len(receipts["items"]) == 1
    assert receipts["items"][0]["message"] == "Second inquiry"


def test_pause_version_permissions_and_tenant_scope(client: TestClient) -> None:
    capture = form(client)
    body = {
        key: capture[key]
        for key in ("name", "title", "description", "source", "enabled", "owner_ids", "version")
    }
    body["enabled"] = False
    assert client.patch(f"/api/v1/capture-forms/{capture['id']}", json=body).status_code == 200
    assert client.patch(f"/api/v1/capture-forms/{capture['id']}", json=body).status_code == 409
    assert submit(client, capture["id"]).status_code == 404
    assert client.get(f"/api/v1/public/forms/{capture['id']}").status_code == 404
    make(
        client,
        "auth/signup",
        {
            "name": "Other",
            "company_name": "Other org",
            "email": "other@capture.test",
            "password": "Secure-password123!",
        },
    )
    assert client.get("/api/v1/capture-forms").json()["total"] == 0
    assert client.get(f"/api/v1/capture-forms/{capture['id']}/submissions").status_code == 404
    assert client.patch(f"/api/v1/capture-forms/{capture['id']}", json=body).status_code == 404
    with Session(cast(Any, client.app).state.engine) as db:
        user = db.scalar(select(User).where(User.email == "other@capture.test"))
        assert user
        user.role = "Sales Rep"
        db.commit()
    assert client.get("/api/v1/capture-forms").status_code == 403


def test_concurrent_submissions_create_one_lead_and_receipt(client: TestClient) -> None:
    capture = form(client)
    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(
            executor.map(lambda _: submit(client, capture["id"], "double-submit"), range(2))
        )
    assert [response.status_code for response in responses] == [201, 201]
    assert client.get("/api/v1/leads").json()["total"] == 1
    assert client.get(f"/api/v1/capture-forms/{capture['id']}/submissions").json()["total"] == 1


def test_inactive_route_does_not_lose_submission_or_silently_assign(client: TestClient) -> None:
    rep = make(
        client,
        "team",
        {
            "name": "Rep",
            "email": "rep@capture.test",
            "password": "Secure-password123!",
            "role": "Sales Rep",
        },
    )
    capture = form(client, owner_ids=[rep["id"]])
    with Session(cast(Any, client.app).state.engine) as db:
        member = db.get(User, rep["id"])
        assert member
        member.is_active = False
        db.commit()
    assert submit(client, capture["id"]).status_code == 503
    assert client.get("/api/v1/leads").json()["total"] == 0
    assert client.get(f"/api/v1/capture-forms/{capture['id']}/submissions").json()["total"] == 0


def test_merge_keeps_capture_inquiry_link_on_retained_lead(client: TestClient) -> None:
    capture = form(client)
    assert submit(client, capture["id"]).status_code == 201
    source = client.get("/api/v1/leads").json()["items"][0]
    target = make(client, "leads", {"name": "Retained customer"})
    response = client.post(f"/api/v1/leads/{source['id']}/merge", json={"target_id": target["id"]})
    assert response.status_code == 200, response.text
    receipts = client.get(f"/api/v1/capture-forms/{capture['id']}/submissions").json()
    assert receipts["items"][0]["lead_id"] == target["id"]
    assert receipts["items"][0]["message"] == "Please contact me"
    replay = client.post(f"/api/v1/leads/{source['id']}/merge", json={"target_id": target["id"]})
    assert replay.status_code == 200 and replay.json()["already_merged"] is True
