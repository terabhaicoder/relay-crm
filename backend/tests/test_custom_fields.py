from concurrent.futures import ThreadPoolExecutor
from typing import Any, cast
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.auth.models import User
from app.modules.crm.tests.test_crm import client as crm_client
from app.modules.crm.tests.test_crm import make
from app.modules.customization.models import FieldAudit, RecordFields
from app.modules.customization.service import copy_compatible_values

client = crm_client
BASE = "/api/v1/custom-fields"


def create_field(client: TestClient, kind: str = "text", **extra: Any) -> dict[str, Any]:
    response = client.post(
        f"{BASE}/definitions",
        json={
            "entity": "leads",
            "field_key": f"field_{uuid4().hex[:8]}",
            "label": kind,
            "field_type": kind,
            **({"options": ["East", "West"]} if kind == "select" else {}),
            **extra,
        },
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert response.status_code == 201, response.text
    return cast(dict[str, Any], response.json())


def values(
    client: TestClient,
    record: dict[str, Any],
    changes: dict[str, Any],
    version: int = 0,
    entity: str = "leads",
    key: str | None = None,
) -> Any:
    return client.patch(
        f"{BASE}/records/{entity}/{record['id']}",
        json={"version": version, "values": changes},
        headers={"Idempotency-Key": key or str(uuid4())},
    )


def get_values(client: TestClient, record: dict[str, Any], entity: str = "leads") -> Any:
    return client.get(f"{BASE}/records/{entity}/{record['id']}")


def test_typed_values_persist_exactly_with_atomic_history_and_retry(client: TestClient) -> None:
    lead = make(client, "leads", {"name": "Typed details"})
    fields = {
        kind: create_field(client, kind) for kind in ("text", "number", "date", "boolean", "select")
    }
    input_values = dict(
        zip(
            [field["id"] for field in fields.values()],
            ["Priority account", "999999999999.123456", "2028-02-29", False, "East"],
            strict=True,
        )
    )
    response = values(client, lead, input_values, key="one-save")
    assert response.status_code == 200, response.text
    assert response.json()["version"] == 1
    assert response.json()["values"] == input_values
    assert len(response.json()["history"][0]["changes"]) == 5
    assert values(client, lead, input_values, key="one-save").json()["version"] == 1
    assert values(client, lead, {fields["text"]["id"]: "Other"}, key="one-save").status_code == 409
    assert (
        values(client, lead, {fields["number"]["id"]: "0.010000"}, version=1).json()["values"][
            fields["number"]["id"]
        ]
        == "0.01"
    )
    with Session(cast(Any, client.app).state.engine) as db:
        stored = db.scalar(select(RecordFields))
        assert stored and stored.values[fields["number"]["id"]] == "0.01"
        assert (
            db.scalar(
                select(func.count())
                .select_from(FieldAudit)
                .where(FieldAudit.record_id == lead["id"])
            )
            == 2
        )


@pytest.mark.parametrize(
    "kind,invalid",
    [
        ("number", 12.1),
        ("number", "NaN"),
        ("number", "1e4"),
        ("number", "1000000000000"),
        ("number", "0.0000001"),
        ("date", "2026-02-29"),
        ("date", "20260101"),
        ("boolean", "false"),
        ("boolean", 0),
        ("select", "North"),
        ("text", True),
    ],
)
def test_invalid_value_does_not_save_other_fields(
    client: TestClient, kind: str, invalid: Any
) -> None:
    lead = make(client, "leads", {"name": "Atomic validation"})
    first, second = create_field(client), create_field(client, kind)
    result = values(client, lead, {first["id"]: "Should not persist", second["id"]: invalid})
    assert result.status_code == 422, result.text
    saved = get_values(client, lead).json()
    assert saved["version"] == 0 and saved["values"] == {} and saved["history"] == []


def test_definition_archive_preserves_values_and_choices_in_use(client: TestClient) -> None:
    field = create_field(client, "select")
    lead = make(client, "leads", {"name": "Retained details"})
    assert values(client, lead, {field["id"]: "East"}).status_code == 200
    path = f"{BASE}/definitions/{field['id']}"
    assert client.patch(path, json={"version": 1, "options": ["West"]}).status_code == 409
    result = client.patch(
        path,
        json={"version": 1, "label": "Territory", "options": ["East", "North"], "archived": True},
    )
    assert result.status_code == 200, result.text
    assert client.get(f"{BASE}/definitions?entity=leads").json()["total"] == 0
    saved = get_values(client, lead).json()
    assert saved["fields"][0]["archived"] is True and saved["values"][field["id"]] == "East"
    assert values(client, lead, {field["id"]: None}, version=1).status_code == 409
    assert client.patch(path, json={"version": 1, "label": "Stale"}).status_code == 409
    assert client.patch(path, json={"version": 2, "archived": False}).status_code == 200
    assert values(client, lead, {field["id"]: None}, version=1).status_code == 200
    assert client.patch(path, json={"version": 3, "options": ["North"]}).status_code == 200


def test_definition_keys_types_and_schema_are_enforced(client: TestClient) -> None:
    field = create_field(client, field_key="fixed_key")
    payload = {
        "entity": "leads",
        "field_key": "fixed_key",
        "label": "Duplicate",
        "field_type": "text",
    }
    assert (
        client.post(
            f"{BASE}/definitions", json=payload, headers={"Idempotency-Key": "duplicate"}
        ).status_code
        == 409
    )
    assert client.post(f"{BASE}/definitions", json=payload).status_code == 422
    assert (
        client.patch(
            f"{BASE}/definitions/{field['id']}", json={"version": 1, "field_type": "number"}
        ).status_code
        == 422
    )
    for extra in (
        {"field_key": "invalid key"},
        {"entity": "invoices"},
        {"required": True},
        {"field_type": "select", "options": ["East", "East"]},
    ):
        assert (
            client.post(
                f"{BASE}/definitions",
                json={**payload, **extra},
                headers={"Idempotency-Key": str(uuid4())},
            ).status_code
            == 422
        )


def test_definition_create_and_initial_save_are_race_safe(client: TestClient) -> None:
    payload = {"entity": "leads", "field_key": "region", "label": "Region", "field_type": "text"}
    with ThreadPoolExecutor(max_workers=2) as pool:
        replies = list(
            pool.map(
                lambda _: client.post(
                    f"{BASE}/definitions",
                    json=payload,
                    headers={"Idempotency-Key": "same-definition"},
                ),
                range(2),
            )
        )
    assert [reply.status_code for reply in replies] == [201, 201]
    assert replies[0].json()["id"] == replies[1].json()["id"]
    field = replies[0].json()
    lead = make(client, "leads", {"name": "Concurrent details"})
    with ThreadPoolExecutor(max_workers=2) as pool:
        replies = list(
            pool.map(lambda value: values(client, lead, {field["id"]: value}), ["East", "West"])
        )
    assert sorted(reply.status_code for reply in replies) == [200, 409]
    assert get_values(client, lead).json()["version"] == 1


def test_custom_fields_obey_record_access_roles_and_tenants(client: TestClient) -> None:
    field = create_field(client)
    lead = make(client, "leads", {"name": "Private lead"})
    make(
        client,
        "team",
        {
            "name": "Rep",
            "email": "rep@fields.test",
            "password": "Rep-password123",
            "role": "Sales Rep",
        },
    )
    assert (
        client.post(
            "/api/v1/auth/login", json={"email": "rep@fields.test", "password": "Rep-password123"}
        ).status_code
        == 200
    )
    assert get_values(client, lead).status_code == 404
    assert values(client, lead, {field["id"]: "Stolen"}).status_code == 404
    assert (
        client.patch(
            f"{BASE}/definitions/{field['id']}", json={"version": 1, "label": "Denied"}
        ).status_code
        == 403
    )
    owned = make(client, "leads", {"name": "Owned lead"})
    assert values(client, owned, {field["id"]: "Allowed"}, key="ownership-retry").status_code == 200
    with Session(cast(Any, client.app).state.engine) as db:
        rep = db.scalar(select(User).where(User.email == "rep@fields.test"))
        assert rep
        rep.role = "Read-only"
        db.commit()
    assert get_values(client, owned).status_code == 200
    assert values(client, owned, {field["id"]: "Allowed"}, key="ownership-retry").status_code == 403
    make(
        client,
        "auth/signup",
        {
            "name": "Other",
            "email": "other@fields.test",
            "password": "Other-password123",
            "company_name": "Other",
        },
    )
    assert get_values(client, lead).status_code == 404
    assert client.get(f"{BASE}/definitions?entity=leads").json()["total"] == 0
    assert (
        client.patch(
            f"{BASE}/definitions/{field['id']}", json={"version": 1, "label": "Denied"}
        ).status_code
        == 404
    )
    other = make(client, "leads", {"name": "Other tenant"})
    assert values(client, other, {field["id"]: "Cross tenant"}).status_code == 404


def test_collection_integrity_and_converted_lead_readonly(client: TestClient) -> None:
    lead = make(client, "leads", {"name": "Qualified"})
    contact_field = create_field(client, entity="contacts")
    assert values(client, lead, {contact_field["id"]: "Wrong collection"}).status_code == 422
    field = create_field(client)
    assert values(client, lead, {field["id"]: "Original"}).status_code == 200
    assert client.post(f"/api/v1/leads/{lead['id']}/convert", json={}).status_code == 200
    assert get_values(client, lead).json()["values"][field["id"]] == "Original"
    assert values(client, lead, {field["id"]: "Changed"}, version=1).status_code == 409
    assert client.get(f"{BASE}/records/calendar/{lead['id']}").status_code == 422


def test_copy_hook_preserves_existing_and_skips_incompatible_choices(client: TestClient) -> None:
    lead = make(client, "leads", {"name": "Source"})
    contact = make(client, "contacts", {"name": "Target"})
    source = create_field(client, field_key="region")
    target = create_field(client, entity="contacts", field_key="region")
    source_choice = create_field(client, "select", field_key="segment")
    target_choice = create_field(
        client, "select", entity="contacts", field_key="segment", options=["North"]
    )
    assert (
        values(client, lead, {source["id"]: "APAC", source_choice["id"]: "East"}).status_code == 200
    )
    engine = cast(Any, client.app).state.engine
    with Session(engine) as db:
        user = db.scalar(select(User))
        assert user
        assert copy_compatible_values(db, user, "leads", lead["id"], "contacts", contact["id"]) == 1
        db.commit()
    result = get_values(client, contact, "contacts").json()
    assert (
        result["values"] == {target["id"]: "APAC"} and target_choice["id"] not in result["values"]
    )
    assert result["history"][0]["action"] == "values_copied"
    assert values(client, lead, {source["id"]: "EMEA"}, version=1).status_code == 200
    with Session(engine) as db:
        user = db.scalar(select(User))
        assert user
        assert copy_compatible_values(db, user, "leads", lead["id"], "contacts", contact["id"]) == 0
        db.commit()
    assert get_values(client, contact, "contacts").json()["values"][target["id"]] == "APAC"


def test_actual_conversion_copies_compatible_fields_to_all_linked_records(
    client: TestClient,
) -> None:
    lead = make(client, "leads", {"name": "Connected fields", "company": "Acme"})
    source = create_field(client, "number", field_key="annual_budget")
    targets = {
        entity: create_field(client, "number", entity=entity, field_key="annual_budget")
        for entity in ("contacts", "parties", "deals")
    }
    assert values(client, lead, {source["id"]: "999999999999.123456"}).status_code == 200
    result = client.post(f"/api/v1/leads/{lead['id']}/convert", json={})
    assert result.status_code == 200, result.text
    converted = result.json()
    for entity, key in (("contacts", "contact"), ("parties", "party"), ("deals", "deal")):
        saved = get_values(client, converted[key], entity).json()
        assert saved["values"] == {targets[entity]["id"]: "999999999999.123456"}
        assert saved["history"][0]["action"] == "values_copied"
        assert saved["version"] == 1
    retry = client.post(f"/api/v1/leads/{lead['id']}/convert", json={})
    assert retry.json()["already_converted"] is True
    assert get_values(client, converted["contact"], "contacts").json()["version"] == 1


def test_actual_merge_fills_unset_custom_values_without_overwrite_or_replay_audit(
    client: TestClient,
) -> None:
    source = make(client, "leads", {"name": "Merge source"})
    target = make(client, "leads", {"name": "Keep target"})
    region = create_field(client, field_key="region")
    budget = create_field(client, "number", field_key="annual_budget")
    opted_in = create_field(client, "boolean", field_key="opted_in")
    assert (
        values(
            client,
            source,
            {
                region["id"]: "Source region",
                budget["id"]: "999999999999.123456",
                opted_in["id"]: True,
            },
        ).status_code
        == 200
    )
    assert (
        values(
            client,
            target,
            {region["id"]: "Target region", budget["id"]: None, opted_in["id"]: False},
        ).status_code
        == 200
    )
    payload = {"target_id": target["id"], "source_version": 1, "target_version": 1}
    response = client.post(f"/api/v1/leads/{source['id']}/merge", json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["already_merged"] is False
    saved = get_values(client, target).json()
    assert saved["values"] == {
        region["id"]: "Target region",
        budget["id"]: "999999999999.123456",
        opted_in["id"]: False,
    }
    assert saved["version"] == 2 and len(saved["history"]) == 2
    copied = saved["history"][0]
    assert copied["action"] == "values_copied"
    assert [change["field_id"] for change in copied["changes"]] == [budget["id"]]
    assert get_values(client, source).status_code == 404
    replay = client.post(f"/api/v1/leads/{source['id']}/merge", json=payload)
    assert replay.status_code == 200 and replay.json()["already_merged"] is True
    after = get_values(client, target).json()
    assert after["values"] == saved["values"]
    assert after["version"] == saved["version"]
    assert after["history"] == saved["history"]
