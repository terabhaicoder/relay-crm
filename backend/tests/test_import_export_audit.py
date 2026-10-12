"""API/database regression checks for real CSV data portability."""

import csv
import io
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.auth.models import User
from app.modules.crm.models import AuditEvent, Lead
from app.modules.crm.tests.test_crm import client as crm_client
from app.modules.crm.tests.test_crm import make

client = crm_client


def rows(response: Any) -> list[dict[str, str]]:
    assert response.status_code == 200, response.text
    return list(csv.DictReader(io.StringIO(response.text.lstrip("\ufeff"))))


def test_export_empty_filters_returns_all_matching_rows(client: TestClient) -> None:
    make(client, "leads", {"name": "QA Alpha", "status": "New"})
    make(client, "leads", {"name": "QA Beta", "status": "Qualified"})
    assert len(rows(client.get("/api/v1/leads/export?q=&status="))) == 2
    assert [r["name"] for r in rows(client.get("/api/v1/leads/export?status=Qualified"))] == [
        "QA Beta"
    ]
    assert len(rows(client.get("/api/v1/leads/export?q=Alpha&owner_id=&stage_id="))) == 1


@pytest.mark.parametrize(
    "content",
    [
        'name,notes\nQA valid,ok\n"unterminated,broken',
        "name,name\nQA one,QA two\n",
        "name,vlaue\nQA typo,123.45\n",
    ],
)
def test_malformed_csv_rejected_before_writing(client: TestClient, content: str) -> None:
    result = client.post("/api/v1/leads/import", json={"csv": content})
    assert result.status_code == 422, result.text
    assert client.get("/api/v1/leads").json()["total"] == 0


def test_ragged_csv_rows_fail_without_partial_records(client: TestClient) -> None:
    result = client.post(
        "/api/v1/leads/import",
        json={
            "csv": (
                "name,email\nQA valid,valid@example.test\n"
                "QA extra,a@example.test,ignored\nQA short\n"
            )
        },
    )
    assert result.status_code == 200, result.text
    assert (result.json()["created"], result.json()["failed"]) == (1, 2)


@pytest.mark.parametrize(
    "entity", ["leads", "contacts", "parties", "deals", "activities", "campaigns", "tickets"]
)
def test_each_collection_csv_roundtrip(client: TestClient, entity: str) -> None:
    original = make(client, entity, {"name": "QA 東京, पुणे", "tags": ["one;two", "हिन्दी"]})
    exported = client.get(f"/api/v1/{entity}/export")
    imported = client.post(
        f"/api/v1/{entity}/import", json={"csv": exported.text, "mode": "update"}
    )
    assert imported.status_code == 200, imported.text
    assert (imported.json()["updated"], imported.json()["failed"]) == (1, 0)
    stored = client.get(f"/api/v1/{entity}/{original['id']}").json()
    assert stored["tags"] == original["tags"]
    assert stored["name"] == original["name"]


def test_thousand_rows_exact_persistence_errors_export_and_retry(client: TestClient) -> None:
    data = io.StringIO()
    writer = csv.writer(data)
    writer.writerow(["name", "email", "phone", "notes", "value", "next_follow_up"])
    for index in range(1000):
        writer.writerow(
            [
                f"QA भारत {index}",
                f"qa{index}@example.test",
                "invalid" if index % 50 == 0 else f"98{index:08d}",
                'Quoted, comma\nand "multiline"',
                "1234.56",
                "2026-10-12T13:00:00+05:30",
            ]
        )
    response = client.post("/api/v1/leads/import", json={"csv": data.getvalue(), "mode": "skip"})
    assert response.status_code == 200, response.text
    result = response.json()
    assert (result["created"], result["failed"], result["skipped"]) == (980, 20, 0)
    assert len(list(csv.DictReader(io.StringIO(result["error_csv"])))) == 20
    with Session(cast(Any, client.app).state.engine) as db:
        assert db.scalar(select(func.count()).select_from(Lead)) == 980
        assert (
            db.scalar(
                select(func.count())
                .select_from(AuditEvent)
                .where(AuditEvent.entity_type == "leads")
            )
            == 980
        )
        saved = db.scalar(select(Lead).where(Lead.email == "qa1@example.test"))
        assert saved is not None
        assert saved.phone == "+919800000001"
        assert str(saved.value) == "1234.56"
        assert saved.notes == 'Quoted, comma\nand "multiline"'
        assert saved.next_follow_up == "2026-10-12T07:30:00+00:00"
    assert len(rows(client.get("/api/v1/leads/export?status="))) == 980
    retry = client.post(
        "/api/v1/leads/import", json={"csv": data.getvalue(), "mode": "skip"}
    ).json()
    assert (retry["created"], retry["skipped"], retry["failed"]) == (0, 980, 20)


def test_export_scope_permissions_and_csv_formula_protection(client: TestClient) -> None:
    own = make(
        client, "leads", {"name": '=HYPERLINK("https://invalid.test")', "phone": "9876543210"}
    )
    other = make(client, "leads", {"name": "QA hidden"})
    with Session(cast(Any, client.app).state.engine) as db:
        user = db.scalar(select(User))
        assert user is not None
        colleague = User(
            org_id=user.org_id,
            name="QA colleague",
            email="colleague@example.test",
            password_hash="unusable",
            role="Sales Rep",
        )
        db.add(colleague)
        db.flush()
        hidden = db.get(Lead, other["id"])
        assert hidden is not None
        hidden.owner_id = colleague.id
        user.role = "Sales Rep"
        db.commit()
    exported = client.get("/api/v1/leads/export")
    data = rows(exported)
    assert len(data) == 1
    assert data[0]["name"].startswith("'=")
    assert data[0]["phone"] == "'+919876543210"
    imported = client.post(
        "/api/v1/leads/import", json={"csv": exported.text, "mode": "update"}
    ).json()
    assert imported["updated"] == 1
    assert client.get(f"/api/v1/leads/{own['id']}").json()["name"] == own["name"]
    with Session(cast(Any, client.app).state.engine) as db:
        user = db.scalar(select(User).where(User.email == "owner@example.com"))
        assert user is not None
        user.role = "Read-only"
        db.commit()
    assert client.post("/api/v1/leads/import", json={"csv": "name\nQA denied"}).status_code == 403
    assert len(rows(client.get("/api/v1/leads/export"))) == 2
    signup = client.post(
        "/api/v1/auth/signup",
        json={
            "name": "QA tenant",
            "email": "tenant@example.test",
            "password": "Test-pass-234!",
            "company_name": "QA tenant",
        },
    )
    assert signup.status_code == 201
    assert rows(client.get("/api/v1/leads/export")) == []


def test_ambiguous_duplicate_update_does_not_overwrite_either_record(client: TestClient) -> None:
    first = make(
        client, "leads", {"name": "QA one", "email": "one@example.test", "phone": "9876543210"}
    )
    second = make(
        client, "leads", {"name": "QA two", "email": "two@example.test", "phone": "9876543211"}
    )
    response = client.post(
        "/api/v1/leads/import",
        json={
            "csv": "name,email,phone\nQA replacement,one@example.test,9876543211\n",
            "mode": "update",
        },
    )
    assert response.status_code == 200, response.text
    assert (response.json()["updated"], response.json()["failed"]) == (0, 1)
    assert "Multiple" in response.json()["error_csv"]
    assert client.get(f"/api/v1/leads/{first['id']}").json()["name"] == "QA one"
    assert client.get(f"/api/v1/leads/{second['id']}").json()["name"] == "QA two"


def test_invalid_deal_row_rolls_back_pipeline_audit_and_record(client: TestClient) -> None:
    from app.modules.crm.models import Deal, Pipeline, Stage

    response = client.post("/api/v1/deals/import", json={"csv": "name,status\nQA invalid,lost\n"})
    assert response.status_code == 200, response.text
    assert (response.json()["created"], response.json()["failed"]) == (0, 1)
    with Session(cast(Any, client.app).state.engine) as db:
        for model in (Deal, Pipeline, Stage, AuditEvent):
            assert db.scalar(select(func.count()).select_from(model)) == 0


def test_import_empty_name_and_invalid_dates_money_are_useful_row_errors(
    client: TestClient,
) -> None:
    make(client, "leads", {"name": "QA existing", "email": "existing@example.test"})
    data = (
        "name,email,value,next_follow_up\n,existing@example.test,10,2026-10-12\n"
        "QA bad date,a@example.test,10,2026-02-30\n"
        "QA bad precision,b@example.test,1.001,2026-10-12\n"
    )
    response = client.post("/api/v1/leads/import", json={"csv": data, "mode": "update"})
    assert response.status_code == 200, response.text
    assert (response.json()["created"], response.json()["updated"], response.json()["failed"]) == (
        0,
        0,
        3,
    )
    assert client.get("/api/v1/leads").json()["total"] == 1
    assert "Name is required" in response.json()["error_csv"]


def test_export_sort_and_literal_apostrophe_roundtrip(client: TestClient) -> None:
    for name in ["QA zulu", "'=literal", "QA alpha"]:
        make(client, "leads", {"name": name})
    exported = client.get("/api/v1/leads/export?sort=name&order=desc")
    data = rows(exported)
    assert [r["name"] for r in data] == ["QA zulu", "QA alpha", "''=literal"]
    result = client.post(
        "/api/v1/leads/import", json={"csv": exported.text, "mode": "update"}
    ).json()
    assert (result["updated"], result["failed"]) == (3, 0)
    assert client.get("/api/v1/leads?q=literal").json()["items"][0]["name"] == "'=literal"
