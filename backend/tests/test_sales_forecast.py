from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.main import create_app
from app.modules.crm.models import Deal


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    app = create_app(
        Settings(environment="test", database_url=SecretStr(f"sqlite:///{tmp_path}/report.db"))
    )
    with TestClient(app) as http:
        assert (
            http.post(
                "/api/v1/auth/signup",
                json={
                    "name": "Reporter",
                    "company_name": "Report QA",
                    "email": "report@example.test",
                    "password": "Report-Password-2026",
                },
            ).status_code
            == 201
        )
        yield http


def deal(client: TestClient, name: str, **fields: Any) -> dict[str, Any]:
    response = client.post("/api/v1/deals", json={"name": name, **fields})
    assert response.status_code == 201, response.text
    return response.json()


def report(client: TestClient, **params: Any) -> dict[str, Any]:
    response = client.get(
        "/api/v1/reports/sales",
        params={"date_from": "2026-10-01", "date_to": "2026-10-31", **params},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_forecast_uses_expected_and_actual_close_dates_and_exact_totals(client: TestClient) -> None:
    first = deal(
        client,
        "Old deal due now",
        amount="100.05",
        probability=50,
        expected_close_date="2026-10-15",
    )
    deal(client, "Future", amount="9999", expected_close_date="2026-12-01")
    deal(client, "No close date", amount="30")
    won = deal(client, "Won now", amount="250.25", expected_close_date="2026-12-01")
    lost = deal(client, "Lost now", amount="75.75")
    assert client.post(f"/api/v1/deals/{won['id']}/won").status_code == 200
    assert (
        client.post(f"/api/v1/deals/{lost['id']}/lost", json={"reason": "Budget"}).status_code
        == 200
    )
    with Session(client.app.state.engine) as db:
        old = db.get(Deal, first["id"])
        assert old
        old.created_at = datetime(2020, 1, 1, tzinfo=UTC)
        for record_id in (won["id"], lost["id"]):
            row = db.get(Deal, record_id)
            assert row
            # 30 September UTC is 1 October IST: include by actual business day.
            row.closed_at = datetime(2026, 9, 30, 20, 0, tzinfo=UTC)
        db.commit()
    result = report(client)
    assert result["summary"]["open_value"] == "100.05"
    assert result["summary"]["weighted_value"] == "10.01"
    assert result["summary"]["won_value"] == "250.25"
    assert result["summary"]["lost_value"] == "75.75"
    assert result["summary"]["win_rate"] == "50.00"
    assert result["summary"]["undated_count"] == 1
    assert result["items"][0]["id"] == first["id"]
    assert report(client, view="won")["items"][0]["close_date"] == "2026-10-01"
    assert report(client, view="lost")["items"][0]["lost_reason"] == "Budget"


def test_forecast_pagination_pipeline_and_tenant_scope(client: TestClient) -> None:
    first = deal(client, "Due A", amount="1.01", expected_close_date="2026-10-10")
    deal(client, "Due B", amount="2.02", expected_close_date="2026-10-20")
    data = report(client, limit=1, offset=1, pipeline_id=first["pipeline_id"])
    assert data["total"] == 2 and len(data["items"]) == 1
    assert data["summary"]["open_value"] == "3.03"
    assert data["items"][0]["name"] == "Due B"
    assert (
        client.post(
            "/api/v1/auth/signup",
            json={
                "name": "Other",
                "company_name": "Other QA",
                "email": "otherreport@example.test",
                "password": "Report-Password-2026",
            },
        ).status_code
        == 201
    )
    assert report(client)["total"] == 0
    assert (
        client.get(
            "/api/v1/reports/sales",
            params={
                "date_from": "2026-10-01",
                "date_to": "2026-10-31",
                "pipeline_id": first["pipeline_id"],
            },
        ).status_code
        == 404
    )


def test_forecast_rejects_invalid_ranges(client: TestClient) -> None:
    for start, end in [("2026-10-31", "2026-10-01"), ("2020-01-01", "2026-12-31")]:
        response = client.get("/api/v1/reports/sales", params={"date_from": start, "date_to": end})
        assert response.status_code == 422


def test_forecast_own_record_and_owner_filters_do_not_leak_other_sales(client: TestClient) -> None:
    rep = client.post(
        "/api/v1/team",
        json={
            "name": "Sales Rep",
            "email": "forecast-rep@example.test",
            "password": "Forecast-Password-2026",
            "role": "Sales Rep",
        },
    )
    assert rep.status_code == 201
    rep_id = rep.json()["id"]
    deal(client, "Private owner sale", amount="50000", expected_close_date="2026-10-10")
    visible = deal(
        client, "Rep sale", owner_id=rep_id, amount="30.25", expected_close_date="2026-10-10"
    )
    assert report(client, owner_id=rep_id)["summary"]["open_value"] == "30.25"
    assert (
        client.post(
            "/api/v1/auth/login",
            json={
                "email": "forecast-rep@example.test",
                "password": "Forecast-Password-2026",
            },
        ).status_code
        == 200
    )
    result = report(client)
    assert result["total"] == 1
    assert result["items"][0]["id"] == visible["id"]
    assert result["summary"]["open_value"] == "30.25"
