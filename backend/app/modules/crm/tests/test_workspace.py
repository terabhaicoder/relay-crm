from datetime import UTC, datetime, timedelta
from typing import Any, cast

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.auth.models import User
from app.modules.crm.models import Deal
from app.modules.crm.tests.test_crm import client as client_fixture
from app.modules.crm.tests.test_crm import make

client = client_fixture


def test_customer_overview_follows_all_links_and_pages(client: TestClient) -> None:
    company = make(client, "parties", {"name": "Customer"})
    contact = make(client, "contacts", {"name": "Buyer", "party_id": company["id"]})
    deal = make(
        client, "deals", {"name": "Contract", "contact_id": contact["id"], "amount": "123.45"}
    )
    ticket = make(client, "tickets", {"name": "Install", "deal_id": deal["id"]})
    for name, entity, record in [
        ("Call", "contacts", contact),
        ("Meeting", "deals", deal),
        ("Followup", "tickets", ticket),
    ]:
        make(client, "activities", {"name": name, "entity_type": entity, "entity_id": record["id"]})
    response = client.get(f"/api/v1/parties/{company['id']}/overview?limit=1")
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["sections"]["contacts"]["total"] == 1
    assert result["sections"]["deals"]["total"] == 1
    assert result["sections"]["tickets"]["total"] == 1
    assert result["sections"]["activities"]["total"] == 3
    assert len(result["sections"]["activities"]["items"]) == 1
    assert result["summary"]["open_pipeline"] == "123.45"
    assert result["summary"]["open_tickets"] == 1
    assert result["timeline"]["total"] >= 7
    second = client.get(f"/api/v1/parties/{company['id']}/overview?limit=1&offset=1").json()
    assert (
        second["sections"]["activities"]["items"][0]["id"]
        != result["sections"]["activities"]["items"][0]["id"]
    )
    assert (
        client.get(f"/api/v1/contacts/{contact['id']}/overview").json()["sections"]["tickets"][
            "total"
        ]
        == 1
    )


def test_campaign_membership_duplicate_conversion_and_remove(client: TestClient) -> None:
    campaign = make(client, "campaigns", {"name": "Event"})
    lead = make(client, "leads", {"name": "Prospect"})
    contact = make(client, "contacts", {"name": "Contact"})
    path = f"/api/v1/campaigns/{campaign['id']}/members"
    payload = {"entity_type": "leads", "entity_id": lead["id"]}
    first = client.post(path, json=payload)
    assert first.status_code == 201, first.text
    assert client.post(path, json=payload).json()["id"] == first.json()["id"]
    assert (
        client.post(path, json={"entity_type": "contacts", "entity_id": contact["id"]}).status_code
        == 201
    )
    assert client.post(f"/api/v1/leads/{lead['id']}/convert", json={}).status_code == 200
    result = client.get(path + "?limit=1").json()
    assert result["total"] == 2 and len(result["items"]) == 1
    assert result["summary"] == {
        "members": 2,
        "leads": 1,
        "contacts": 1,
        "converted_leads": 1,
        "conversion_rate": 100.0,
    }
    assert client.delete(path + "/" + first.json()["id"]).status_code == 204
    assert client.get(path).json()["total"] == 1


def test_campaign_merge_preserves_members_and_deduplicates(client: TestClient) -> None:
    target = make(client, "leads", {"name": "Target"})
    source = make(client, "leads", {"name": "Source"})
    campaigns = [make(client, "campaigns", {"name": name}) for name in ["One", "Two"]]
    for campaign in campaigns:
        assert (
            client.post(
                f"/api/v1/campaigns/{campaign['id']}/members",
                json={"entity_type": "leads", "entity_id": source["id"]},
            ).status_code
            == 201
        )
    client.post(
        f"/api/v1/campaigns/{campaigns[0]['id']}/members",
        json={"entity_type": "leads", "entity_id": target["id"]},
    )
    assert (
        client.post(
            f"/api/v1/leads/{source['id']}/merge", json={"target_id": target["id"]}
        ).status_code
        == 200
    )
    for campaign in campaigns:
        result = client.get(f"/api/v1/campaigns/{campaign['id']}/members").json()
        assert result["total"] == 1
        assert result["items"][0]["entity_id"] == target["id"]


def test_calendar_complete_counts_preview_and_ist_dates(client: TestClient) -> None:
    for index in range(6):
        make(client, "activities", {"name": f"Task {index}", "due_date": "2026-10-12"})
    make(client, "activities", {"name": "UTC evening", "due_date": "2026-10-11T20:00:00Z"})
    make(client, "activities", {"name": "Other month", "due_date": "2026-11-01"})
    result = client.get("/api/v1/calendar?from_date=2026-10-01&to_date=2026-10-31")
    assert result.status_code == 200, result.text
    data = result.json()
    assert data["total"] == 7
    day = next(row for row in data["days"] if row["date"] == "2026-10-12")
    assert day["count"] == 7 and len(day["items"]) == 3
    records = client.get(
        "/api/v1/activities?date_from=2026-10-12&date_to=2026-10-12&limit=2&offset=2"
    ).json()
    assert records["total"] == 7 and len(records["items"]) == 2
    assert client.get("/api/v1/calendar?from_date=2026-01-01&to_date=2026-12-01").status_code == 422
    assert (
        client.get("/api/v1/activities?date_from=2026-10-13&date_to=2026-10-12").status_code == 422
    )


def test_board_summary_and_pipeline_filter_exact_money(client: TestClient) -> None:
    pipeline = client.get("/api/v1/pipelines").json()["items"][0]
    other = make(client, "pipelines", {"name": "Other"})
    for index in range(3):
        make(
            client,
            "deals",
            {
                "name": f"Acme {index}",
                "amount": "0.10",
                "pipeline_id": pipeline["id"],
                "stage_id": pipeline["stages"][0]["id"],
            },
        )
    make(
        client,
        "deals",
        {"name": "Elsewhere", "pipeline_id": other["id"], "stage_id": other["stages"][0]["id"]},
    )
    summary = client.get(f"/api/v1/deals/board-summary?pipeline_id={pipeline['id']}&q=Acme").json()
    assert summary["stages"][0]["total"] == 3
    assert summary["stages"][0]["amount"] == "0.30"
    records = client.get(f"/api/v1/deals?pipeline_id={pipeline['id']}&limit=1").json()
    assert records["total"] == 3 and len(records["items"]) == 1


def test_pipeline_stage_configuration_and_used_stage_protection(client: TestClient) -> None:
    pipeline = client.get("/api/v1/pipelines").json()["items"][0]
    stages = [
        {key: stage[key] for key in ["id", "name", "category", "probability"]}
        for stage in pipeline["stages"]
    ]
    stages.insert(1, {"name": "Demo", "category": "open", "probability": 25})
    updated = client.patch(
        f"/api/v1/pipelines/{pipeline['id']}", json={"name": "Enterprise", "stages": stages}
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["stages"][1]["name"] == "Demo"
    make(client, "deals", {"name": "Protected", "stage_id": stages[0]["id"]})
    assert (
        client.patch(f"/api/v1/pipelines/{pipeline['id']}", json={"stages": stages[1:]}).status_code
        == 409
    )
    stages[0]["category"] = "lost"
    assert (
        client.patch(f"/api/v1/pipelines/{pipeline['id']}", json={"stages": stages}).status_code
        == 422
    )
    assert client.get("/api/v1/pipelines").json()["items"][0]["stages"][0]["category"] == "open"


def test_workbench_complete_task_and_stalled_deal(client: TestClient) -> None:
    task = make(client, "activities", {"name": "Overdue", "due_date": "2001-01-01"})
    lead = make(client, "leads", {"name": "Needs follow-up"})
    deal = make(client, "deals", {"name": "Stale"})
    with Session(cast(Any, client.app).state.engine) as db:
        row = db.get(Deal, deal["id"])
        assert row is not None
        row.stage_entered_at = datetime.now(UTC) - timedelta(days=30)
        db.commit()
    data = client.get("/api/v1/workbench?queue=overdue").json()
    assert data["counts"]["overdue"] == 1 and data["counts"]["stale_deals"] == 1
    assert data["items"][0]["id"] == task["id"]
    assert data["items"][0]["entity_type"] == "activities"
    assert client.post(f"/api/v1/activities/{task['id']}/complete").status_code == 200
    assert client.get("/api/v1/workbench").json()["counts"]["overdue"] == 0
    assert (
        client.get("/api/v1/workbench?queue=follow_up_leads").json()["items"][0]["id"] == lead["id"]
    )


def test_workspace_endpoints_tenant_and_own_record_scope(client: TestClient) -> None:
    company = make(client, "parties", {"name": "Private company"})
    campaign = make(client, "campaigns", {"name": "Private campaign"})
    lead = make(client, "leads", {"name": "Private lead"})
    pipeline = client.get("/api/v1/pipelines").json()["items"][0]
    client.post("/api/v1/auth/logout")
    signup = client.post(
        "/api/v1/auth/signup",
        json={
            "name": "Other",
            "email": "other@example.com",
            "password": "Test-pass-234!",
            "company_name": "Other",
        },
    )
    assert signup.status_code == 201
    assert client.get(f"/api/v1/parties/{company['id']}/overview").status_code == 404
    assert client.get(f"/api/v1/campaigns/{campaign['id']}/members").status_code == 404
    assert (
        client.get(f"/api/v1/deals/board-summary?pipeline_id={pipeline['id']}").status_code == 404
    )
    own_campaign = make(client, "campaigns", {"name": "Own campaign"})
    assert (
        client.post(
            f"/api/v1/campaigns/{own_campaign['id']}/members",
            json={"entity_type": "leads", "entity_id": lead["id"]},
        ).status_code
        == 404
    )
    own_lead = make(client, "leads", {"name": "Own lead"})
    with Session(cast(Any, client.app).state.engine) as db:
        user = db.scalar(select(User).where(User.email == "other@example.com"))
        assert user is not None
        user.role = "Sales Rep"
        db.commit()
    result = client.get("/api/v1/workbench?queue=follow_up_leads").json()
    assert [row["id"] for row in result["items"]] == [own_lead["id"]]


def test_customer_and_campaign_sections_hide_records_owned_by_others(client: TestClient) -> None:
    from app.modules.crm.models import Contact, Lead

    company = make(client, "parties", {"name": "Visible company"})
    contact = make(client, "contacts", {"name": "Hidden contact", "party_id": company["id"]})
    lead = make(client, "leads", {"name": "Hidden lead"})
    campaign = make(client, "campaigns", {"name": "Visible campaign"})
    client.post(
        f"/api/v1/campaigns/{campaign['id']}/members",
        json={"entity_type": "leads", "entity_id": lead["id"]},
    )
    with Session(cast(Any, client.app).state.engine) as db:
        user = db.scalar(select(User).where(User.email == "owner@example.com"))
        assert user is not None
        user.role = "Sales Rep"
        hidden_contact = db.get(Contact, contact["id"])
        hidden_lead = db.get(Lead, lead["id"])
        assert hidden_contact is not None and hidden_lead is not None
        hidden_contact.owner_id = None
        hidden_lead.owner_id = None
        db.commit()
    overview = client.get(f"/api/v1/parties/{company['id']}/overview").json()
    assert overview["sections"]["contacts"]["total"] == 0
    assert all(row["entity_id"] != contact["id"] for row in overview["timeline"]["items"])
    members = client.get(f"/api/v1/campaigns/{campaign['id']}/members").json()
    assert members["total"] == 0 and members["summary"]["leads"] == 0


def test_membership_concurrent_retry_creates_one_link(client: TestClient) -> None:
    from concurrent.futures import ThreadPoolExecutor

    campaign = make(client, "campaigns", {"name": "Campaign"})
    lead = make(client, "leads", {"name": "Lead"})
    path = f"/api/v1/campaigns/{campaign['id']}/members"

    def add() -> Any:
        return client.post(path, json={"entity_type": "leads", "entity_id": lead["id"]})

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: add(), range(2)))
    assert all(response.status_code == 201 for response in responses)
    assert responses[0].json()["id"] == responses[1].json()["id"]
    assert client.get(path).json()["total"] == 1


def test_pipeline_create_rejects_duplicate_reserved_blank_stage_names(client: TestClient) -> None:
    for stages in [["Discovery", "discovery"], ["Won"], [" "]]:
        assert (
            client.post("/api/v1/pipelines", json={"name": "Bad", "stages": stages}).status_code
            == 422
        )


def test_calendar_summary_matches_agenda_search_and_status(client: TestClient) -> None:
    first = make(client, "activities", {"name": "Call Alpha", "due_date": "2026-10-12"})
    make(client, "activities", {"name": "Meeting Beta", "due_date": "2026-10-12"})
    make(client, "activities", {"name": "Call Gamma", "due_date": "2026-10-12"})
    client.post(f"/api/v1/activities/{first['id']}/complete")
    summary = client.get(
        "/api/v1/calendar?from_date=2026-10-12&to_date=2026-10-12&q=Call&status=pending"
    ).json()
    agenda = client.get(
        "/api/v1/activities?date_from=2026-10-12&date_to=2026-10-12&q=Call&status=pending"
    ).json()
    assert (
        client.get("/api/v1/calendar?from_date=2026-10-12&to_date=2026-10-12&status=").json()[
            "total"
        ]
        == 3
    )
    assert summary["total"] == agenda["total"] == 1
    assert summary["days"][0]["items"][0]["name"] == agenda["items"][0]["name"] == "Call Gamma"


def test_unassigned_queue_counts_remain_visible_in_my_work(client: TestClient) -> None:
    ticket = make(client, "tickets", {"name": "Unassigned request"})
    assert (
        client.patch(f"/api/v1/tickets/{ticket['id']}", json={"owner_id": None}).status_code == 200
    )
    owner = client.get("/api/v1/me").json()["id"]
    data = client.get(f"/api/v1/workbench?queue=unassigned_tickets&owner_id={owner}").json()
    assert data["total"] == data["counts"]["unassigned_tickets"] == 1
    assert data["items"][0]["id"] == ticket["id"]


def test_deal_export_respects_pipeline_and_other_active_filters(client: TestClient) -> None:
    import csv
    import io

    pipeline = client.get("/api/v1/pipelines").json()["items"][0]
    other = make(client, "pipelines", {"name": "Renewals"})
    for name, target in [
        ("Match first", pipeline),
        ("Excluded search", pipeline),
        ("Match other", other),
    ]:
        make(
            client,
            "deals",
            {
                "name": name,
                "pipeline_id": target["id"],
                "stage_id": target["stages"][0]["id"],
                "amount": "19.95",
            },
        )
    exported = client.get(f"/api/v1/deals/export?pipeline_id={pipeline['id']}&q=Match&status=open")
    assert exported.status_code == 200, exported.text
    rows = list(csv.DictReader(io.StringIO(exported.text)))
    assert [row["name"] for row in rows] == ["Match first"]
    assert rows[0]["pipeline_id"] == pipeline["id"]
    assert rows[0]["amount"] == "19.95"
    all_rows = client.get(f"/api/v1/deals/export?pipeline_id={pipeline['id']}")
    assert len(list(csv.DictReader(io.StringIO(all_rows.text)))) == 2
    make(client, "contacts", {"name": "Existing export"})
    assert client.get("/api/v1/contacts/export").status_code == 200
