"""Quotation commercial lifecycle uses real SQLite and real CRM transactions."""

from concurrent.futures import ThreadPoolExecutor
from typing import Any, cast
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.auth.models import User
from app.modules.commercial import service as commercial_service
from app.modules.commercial.models import Quotation, QuotationEvent, QuotationLine
from app.modules.crm.models import Deal
from app.modules.crm.tests.test_crm import client as crm_client
from app.modules.crm.tests.test_crm import make

client = crm_client


def payload(client: TestClient) -> dict[str, Any]:
    party = make(client, "parties", {"name": "Quotation customer"})
    deal = make(client, "deals", {"name": "Implementation", "party_id": party["id"]})
    return {
        "deal_id": deal["id"],
        "name": "Implementation quotation",
        "lines": [
            {"description": "Consulting", "quantity": "1.005", "unit_price": "100.0000"},
            {"description": "Setup", "quantity": "3", "unit_price": "0.3350"},
        ],
        "discount": "1.00",
        "terms": "Tax excluded. Payment on agreed terms.",
    }


def post(client: TestClient, path: str, body: dict[str, Any], key: str | None = None) -> Any:
    return client.post(
        f"/api/v1{path}", json=body, headers={"Idempotency-Key": key or str(uuid4())}
    )


def create(client: TestClient, body: dict[str, Any]) -> dict[str, Any]:
    response = post(client, "/quotations", body)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


def test_quote_to_won_exact_money_snapshot_and_retry(client: TestClient) -> None:
    body = payload(client)
    quote = create(client, body)
    assert (quote["subtotal"], quote["discount"], quote["total"]) == ("101.51", "1.00", "100.51")
    assert quote["lines"][1]["amount"] == "1.01"
    issued = post(client, f"/quotations/{quote['id']}/issue", {"version": 1}).json()
    assert issued["status"] == "issued"
    patch = {key: value for key, value in body.items() if key != "deal_id"}
    assert (
        client.patch(f"/api/v1/quotations/{quote['id']}", json={**patch, "version": 2}).status_code
        == 409
    )
    decision = {
        "version": 2,
        "note": "Customer approved by phone, reference ABC",
        "close_deal": True,
        "deal_version": 1,
    }
    first = post(client, f"/quotations/{quote['id']}/accept", decision, "decision-key")
    assert first.status_code == 200, first.text
    retry = post(client, f"/quotations/{quote['id']}/accept", decision, "decision-key")
    assert retry.status_code == 200
    assert retry.json()["version"] == 3
    deal = client.get(f"/api/v1/deals/{body['deal_id']}").json()
    assert (deal["status"], deal["amount"]) == ("won", "100.51")
    history = client.get(f"/api/v1/deals/{deal['id']}/history").json()["items"]
    assert len(history) == 2
    assert any(event["to_stage_id"] == deal["stage_id"] for event in history)
    with Session(cast(Any, client.app).state.engine) as db:
        assert db.scalar(select(func.count()).select_from(Quotation)) == 1
        assert db.scalar(select(func.count()).select_from(QuotationLine)) == 2
        assert db.scalar(select(func.count()).select_from(QuotationEvent)) == 3


def test_draft_edit_validation_stale_version_and_expiry(client: TestClient) -> None:
    body = payload(client)
    assert client.post("/api/v1/quotations", json=body).status_code == 422
    assert post(client, "/quotations", {**body, "discount": "1000"}).status_code == 422
    assert (
        post(
            client,
            "/quotations",
            {**body, "lines": [{"description": "Bad", "quantity": "0", "unit_price": "1"}]},
        ).status_code
        == 422
    )
    assert (
        post(
            client,
            "/quotations",
            {**body, "lines": [{"description": "Bad", "quantity": "1", "unit_price": "NaN"}]},
        ).status_code
        == 422
    )
    quote = create(client, body)
    patch = {key: value for key, value in body.items() if key != "deal_id"}
    edit = {**patch, "version": 1, "discount": "0.51", "valid_until": "2000-01-01"}
    result = client.patch(f"/api/v1/quotations/{quote['id']}", json=edit)
    assert result.status_code == 200, result.text
    assert result.json()["total"] == "101.00"
    assert client.patch(f"/api/v1/quotations/{quote['id']}", json=edit).status_code == 409
    assert post(client, f"/quotations/{quote['id']}/issue", {"version": 2}).status_code == 409
    with Session(cast(Any, client.app).state.engine) as db:
        assert db.scalar(select(func.count()).select_from(QuotationLine)) == 2


def test_permission_tenant_and_current_owner_scope(client: TestClient) -> None:
    body = payload(client)
    quote = create(client, body)
    engine = cast(Any, client.app).state.engine
    with Session(engine) as db:
        user = db.scalar(select(User))
        assert user
        user.role = "Read-only"
        db.commit()
    assert post(client, f"/quotations/{quote['id']}/issue", {"version": 1}).status_code == 403
    with Session(engine) as db:
        user = db.scalar(select(User))
        deal = db.get(Deal, body["deal_id"])
        assert user and deal
        user.role = "Sales Rep"
        deal.owner_id = None
        db.commit()
    assert client.get(f"/api/v1/quotations/{quote['id']}").status_code == 404
    assert client.get("/api/v1/quotations").json()["total"] == 0
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "name": "Other",
            "email": "other-quote@example.test",
            "company_name": "Other",
            "password": "Test-tenant-123!",
        },
    )
    assert response.status_code == 201
    assert client.get(f"/api/v1/quotations/{quote['id']}").status_code == 404
    assert post(client, "/quotations", body).status_code == 404


def test_acceptance_failure_rolls_back_and_decision_required(client: TestClient) -> None:
    body = payload(client)
    quote = create(client, body)
    post(client, f"/quotations/{quote['id']}/issue", {"version": 1})
    assert post(client, f"/quotations/{quote['id']}/accept", {"version": 2}).status_code == 422
    response = post(
        client,
        f"/quotations/{quote['id']}/accept",
        {"version": 2, "note": "Approved", "close_deal": True, "deal_version": 999},
    )
    assert response.status_code == 409
    assert client.get(f"/api/v1/quotations/{quote['id']}").json()["status"] == "issued"
    assert client.get(f"/api/v1/deals/{body['deal_id']}").json()["status"] == "open"
    declined = post(
        client,
        f"/quotations/{quote['id']}/decline",
        {"version": 2, "note": "Customer deferred budget"},
    )
    assert declined.status_code == 200
    assert declined.json()["status"] == "declined"
    assert client.get(f"/api/v1/deals/{body['deal_id']}").json()["status"] == "open"


def test_concurrent_idempotent_create_and_single_decision(client: TestClient) -> None:
    body = payload(client)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(lambda _: post(client, "/quotations", body, "concurrent-create"), range(2))
        )
    assert [result.status_code for result in results] == [201, 201]
    assert results[0].json()["id"] == results[1].json()["id"]
    quote = results[0].json()
    assert (
        post(client, "/quotations", {**body, "name": "changed"}, "concurrent-create").status_code
        == 409
    )
    post(client, f"/quotations/{quote['id']}/issue", {"version": 1})
    with ThreadPoolExecutor(max_workers=2) as pool:
        decisions = list(
            pool.map(
                lambda action: post(
                    client,
                    f"/quotations/{quote['id']}/{action}",
                    {"version": 2, "note": "Recorded decision"},
                ),
                ["accept", "decline"],
            )
        )
    assert sorted(result.status_code for result in decisions) == [200, 409]


def test_acceptance_failure_after_deal_write_rolls_back_both_modules(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    body = payload(client)
    quote = create(client, body)
    assert post(client, f"/quotations/{quote['id']}/issue", {"version": 1}).status_code == 200

    def fail_audit(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("Deliberate test failure after deal mutation")

    monkeypatch.setattr(commercial_service, "audit", fail_audit)
    with pytest.raises(RuntimeError, match="Deliberate test failure"):
        post(
            client,
            f"/quotations/{quote['id']}/accept",
            {"version": 2, "note": "Approved", "close_deal": True, "deal_version": 1},
        )
    persisted_quote = client.get(f"/api/v1/quotations/{quote['id']}").json()
    persisted_deal = client.get(f"/api/v1/deals/{body['deal_id']}").json()
    assert (persisted_quote["status"], persisted_quote["version"]) == ("issued", 2)
    assert (persisted_deal["status"], persisted_deal["amount"], persisted_deal["version"]) == (
        "open",
        "0.00",
        1,
    )
    history = client.get(f"/api/v1/deals/{body['deal_id']}/history").json()["items"]
    assert len(history) == 1


@pytest.mark.parametrize("status", ["draft", "issued", "accepted", "declined"])
def test_list_filter_and_pagination(client: TestClient, status: str) -> None:
    quote = create(client, payload(client))
    if status != "draft":
        post(client, f"/quotations/{quote['id']}/issue", {"version": 1})
    if status in {"accepted", "declined"}:
        post(
            client,
            f"/quotations/{quote['id']}/{'accept' if status == 'accepted' else 'decline'}",
            {"version": 2, "note": "Customer decision"},
        )
    result = client.get(f"/api/v1/quotations?status={status}&q=Implementation&limit=1").json()
    assert result["total"] == 1
    assert result["items"][0]["id"] == quote["id"]
    result = client.get(f"/api/v1/quotations?status={status}&offset=1&limit=1").json()
    assert result["total"] == 1 and result["items"] == []
