"""CRM changes must preserve the quotation module's retained document links."""

from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.modules.crm.tests.test_crm import client as crm_client
from app.modules.crm.tests.test_crm import make

client = crm_client


def post(client: TestClient, path: str, body: dict[str, Any]) -> Any:
    return client.post(f"/api/v1{path}", json=body, headers={"Idempotency-Key": str(uuid4())})


@pytest.mark.parametrize("status", ["draft", "issued", "accepted", "declined"])
def test_quotation_history_blocks_archive_and_reparent(client: TestClient, status: str) -> None:
    party = make(client, "parties", {"name": "Historical account"})
    contact = make(client, "contacts", {"name": "Historical contact", "party_id": party["id"]})
    deal = make(
        client,
        "deals",
        {"name": "Quoted opportunity", "party_id": party["id"], "contact_id": contact["id"]},
    )
    response = post(
        client,
        "/quotations",
        {
            "name": "Retained quote",
            "deal_id": deal["id"],
            "lines": [{"description": "Service", "quantity": "1", "unit_price": "100.00"}],
        },
    )
    assert response.status_code == 201, response.text
    quote = response.json()
    if status != "draft":
        assert post(client, f"/quotations/{quote['id']}/issue", {"version": 1}).status_code == 200
    if status in {"accepted", "declined"}:
        action = "accept" if status == "accepted" else "decline"
        assert (
            post(
                client,
                f"/quotations/{quote['id']}/{action}",
                {"version": 2, "note": "Recorded customer decision"},
            ).status_code
            == 200
        )
    for entity, record in (("deals", deal), ("contacts", contact), ("parties", party)):
        assert client.delete(f"/api/v1/{entity}/{record['id']}").status_code == 409
        assert client.get(f"/api/v1/{entity}/{record['id']}").json()["version"] == record["version"]
    for key in ("party_id", "contact_id"):
        assert client.patch(f"/api/v1/deals/{deal['id']}", json={key: None}).status_code == 409
    assert (
        client.patch(f"/api/v1/contacts/{contact['id']}", json={"party_id": None}).status_code
        == 409
    )
    renamed = client.patch(f"/api/v1/parties/{party['id']}", json={"name": "Current account name"})
    assert renamed.status_code == 200
    stored = client.get(f"/api/v1/quotations/{quote['id']}").json()
    assert stored["status"] == status
    assert stored["customer_name"] == "Historical account"
    # Normal deal progression remains permitted; it does not reparent the quote.
    assert client.post(f"/api/v1/deals/{deal['id']}/won").status_code == 200


def test_unquoted_record_can_still_change_company_and_archive(client: TestClient) -> None:
    first = make(client, "parties", {"name": "First"})
    second = make(client, "parties", {"name": "Second"})
    deal = make(client, "deals", {"name": "Unquoted", "party_id": first["id"]})
    assert (
        client.patch(f"/api/v1/deals/{deal['id']}", json={"party_id": second["id"]}).status_code
        == 200
    )
    assert client.delete(f"/api/v1/deals/{deal['id']}").status_code == 204
    assert client.delete(f"/api/v1/parties/{first['id']}").status_code == 204
    assert client.delete(f"/api/v1/parties/{second['id']}").status_code == 204
