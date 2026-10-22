from concurrent.futures import ThreadPoolExecutor
from typing import Any, cast
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.auth.models import User
from app.modules.crm.tests.test_crm import client as crm_client
from app.modules.crm.tests.test_crm import make

client = crm_client


def body(**filters: Any) -> dict[str, Any]:
    return {
        "name": "Qualified website leads",
        "entity": "leads",
        "filters": {"q": "Website", "status": "Qualified", "sort": "name:asc", **filters},
    }


def create(client: TestClient, payload: dict[str, Any], key: str | None = None) -> Any:
    return client.post(
        "/api/v1/saved-views", json=payload, headers={"Idempotency-Key": key or str(uuid4())}
    )


def test_saved_view_create_replay_update_list_and_delete(client: TestClient) -> None:
    first = create(client, body(), "retry-key")
    assert first.status_code == 201, first.text
    record = first.json()
    retry = create(client, body(), "retry-key")
    assert retry.json()["id"] == record["id"]
    assert create(client, {**body(), "name": "Changed payload"}, "retry-key").status_code == 409
    listing = client.get("/api/v1/saved-views?entity=leads&limit=1").json()
    assert listing["total"] == 1
    assert listing["items"][0]["filters"]["status"] == "Qualified"
    assert client.get("/api/v1/saved-views?entity=contacts").json()["total"] == 0
    assert client.get("/api/v1/saved-views?entity=leads&offset=1&limit=1").json()["items"] == []
    edit = {"name": "Contacted leads", "filters": {"status": "Contacted"}, "version": 1}
    response = client.patch(f"/api/v1/saved-views/{record['id']}", json=edit)
    assert response.status_code == 200
    assert response.json()["version"] == 2
    assert client.patch(f"/api/v1/saved-views/{record['id']}", json=edit).status_code == 409
    assert client.delete(f"/api/v1/saved-views/{record['id']}").status_code == 204
    assert client.get(f"/api/v1/saved-views/{record['id']}").status_code == 404
    assert create(client, body(), "retry-key").status_code == 404


def test_readonly_can_manage_private_preferences_but_not_business_records(
    client: TestClient,
) -> None:
    engine = cast(Any, client.app).state.engine
    with Session(engine) as db:
        user = db.scalar(select(User))
        assert user
        user.role = "Read-only"
        db.commit()
    response = create(client, body())
    assert response.status_code == 201, response.text
    assert client.post("/api/v1/leads", json={"name": "Forbidden"}).status_code == 403
    assert client.delete(f"/api/v1/saved-views/{response.json()['id']}").status_code == 204


def test_views_are_private_even_from_same_org_admin_and_other_tenant(client: TestClient) -> None:
    record = create(client, body()).json()
    make(
        client,
        "team",
        {
            "name": "Admin",
            "email": "admin@views.test",
            "password": "Admin-password123",
            "role": "Admin",
        },
    )
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"email": "admin@views.test", "password": "Admin-password123"},
        ).status_code
        == 200
    )
    for stage in ("same_org", "another_org"):
        if stage == "another_org":
            make(
                client,
                "auth/signup",
                {
                    "name": "Other",
                    "email": "other@views.test",
                    "password": "Other-password123",
                    "company_name": "Other",
                },
            )
        assert client.get("/api/v1/saved-views?entity=leads").json()["total"] == 0
        assert client.get(f"/api/v1/saved-views/{record['id']}").status_code == 404
        assert (
            client.patch(
                f"/api/v1/saved-views/{record['id']}",
                json={"name": "Not mine", "filters": {}, "version": 1},
            ).status_code
            == 404
        )
        assert client.delete(f"/api/v1/saved-views/{record['id']}").status_code == 404
        # Names and retry keys are scoped to the current individual.
        assert create(client, body(), "same-key").status_code == 201


@pytest.mark.parametrize(
    "filters",
    [
        {"unknown": True},
        {"status": "won"},
        {"sort": "email:asc"},
        {"sort": "name:sideways"},
        {"view": "board"},
        {"pipeline_id": "invalid"},
    ],
)
def test_filters_reject_unsupported_semantics(client: TestClient, filters: dict[str, Any]) -> None:
    assert create(client, body(**filters)).status_code == 422


def test_collection_pipeline_reference_and_key_validation(client: TestClient) -> None:
    assert client.post("/api/v1/saved-views", json=body()).status_code == 422
    assert create(client, {**body(), "entity": "calendar"}).status_code == 422
    pipe = client.get("/api/v1/pipelines").json()["items"][0]
    good = {
        "name": "Open pipeline",
        "entity": "deals",
        "filters": {"status": "open", "pipeline_id": pipe["id"], "view": "table"},
    }
    assert create(client, good).status_code == 201
    make(
        client,
        "auth/signup",
        {
            "name": "Other",
            "email": "other@pipeline.test",
            "password": "Other-password123",
            "company_name": "Other",
        },
    )
    assert create(client, good).status_code == 404


def test_simultaneous_create_retries_keep_one_view(client: TestClient) -> None:
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: create(client, body(), "concurrent-view"), range(2)))
    assert [response.status_code for response in responses] == [201, 201]
    assert responses[0].json()["id"] == responses[1].json()["id"]
    assert client.get("/api/v1/saved-views?entity=leads").json()["total"] == 1
