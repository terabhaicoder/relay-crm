from pathlib import Path

from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.config import Settings
from app.main import create_app


def test_sales_visibility_link_checks_and_engagement_tenant_guards(tmp_path: Path) -> None:
    app = create_app(
        Settings(database_url=SecretStr(f"sqlite:///{tmp_path}/audit.db"), environment="test")
    )
    with TestClient(app) as client:
        owner = client.post(
            "/api/v1/auth/signup",
            json={
                "name": "Owner",
                "company_name": "Company A",
                "email": "owner@a.example",
                "password": "Owner-password123",
            },
        ).json()
        owner_token = client.cookies.get("erp_session")
        hidden_party = client.post(
            "/api/v1/parties", json={"name": "Owner's private account"}
        ).json()
        hidden_lead = client.post("/api/v1/leads", json={"name": "Owner's private lead"}).json()
        rule = client.post(
            "/api/v1/automations",
            json={
                "name": "Lead follow-up",
                "trigger": "leads.created",
                "action": "notify",
                "action_text": "Contact {{name}}",
            },
        ).json()
        draft = client.post(
            "/api/v1/email/messages",
            json={
                "recipient": "buyer@example.com",
                "subject": "Private draft",
                "body": "Draft content",
            },
        ).json()
        template = client.post(
            "/api/v1/email/templates",
            json={"name": "Welcome", "subject": "Welcome", "body": "Hello"},
        ).json()
        assert (
            client.post(
                "/api/v1/team",
                json={
                    "name": "Rep",
                    "email": "rep@a.example",
                    "password": "Rep-password123",
                    "role": "Sales Rep",
                },
            ).status_code
            == 201
        )
        assert (
            client.post(
                "/api/v1/auth/login", json={"email": "rep@a.example", "password": "Rep-password123"}
            ).status_code
            == 200
        )
        assert client.get(f"/api/v1/leads/{hidden_lead['id']}").status_code == 404
        assert client.get("/api/v1/leads").json()["total"] == 0
        assert (
            client.post(
                "/api/v1/contacts", json={"name": "Forbidden link", "party_id": hidden_party["id"]}
            ).status_code
            == 404
        )
        assert (
            client.post(
                "/api/v1/activities",
                json={
                    "name": "Forbidden activity",
                    "entity_type": "leads",
                    "entity_id": hidden_lead["id"],
                },
            ).status_code
            == 404
        )
        assert (
            client.post(
                "/api/v1/leads", json={"name": "Cannot assign owner", "owner_id": owner["id"]}
            ).status_code
            == 403
        )
        assert client.get("/api/v1/email/messages").json()["items"] == []
        assert client.delete(f"/api/v1/email/messages/{draft['id']}").status_code == 404
        own_lead = client.post("/api/v1/leads", json={"name": "Rep's own lead"}).json()
        assert client.get(f"/api/v1/leads/{own_lead['id']}").status_code == 200
        own_notifications = client.get("/api/v1/notifications").json()["items"]
        assert len(own_notifications) == 1
        assert own_notifications[0]["entity_id"] == own_lead["id"]
        client.post(
            "/api/v1/auth/signup",
            json={
                "name": "Other Owner",
                "company_name": "Company B",
                "email": "owner@b.example",
                "password": "Other-password123",
            },
        )
        assert (
            client.patch(f"/api/v1/automations/{rule['id']}", json={"enabled": False}).status_code
            == 404
        )
        assert client.delete(f"/api/v1/email/templates/{template['id']}").status_code == 404
        assert (
            client.post(f"/api/v1/notifications/{own_notifications[0]['id']}/read").status_code
            == 404
        )
        assert client.get(f"/api/v1/leads/{own_lead['id']}/timeline").status_code == 404
        assert (
            client.post(
                "/api/v1/email/messages",
                json={
                    "recipient": "buyer@example.com",
                    "subject": "Foreign link",
                    "body": "Text",
                    "entity_type": "leads",
                    "entity_id": hidden_lead["id"],
                },
            ).status_code
            == 404
        )
        client.cookies.clear()
        client.cookies.set("erp_session", owner_token)
        reader = client.post(
            "/api/v1/team",
            json={
                "name": "Reader",
                "email": "reader@a.example",
                "password": "Reader-password123",
                "role": "Read-only",
            },
        )
        assert reader.status_code == 201
        client.post(
            "/api/v1/auth/login",
            json={"email": "reader@a.example", "password": "Reader-password123"},
        )
        for path, payload in [
            ("/leads", {"name": "Forbidden"}),
            ("/email/templates", {"name": "Forbidden", "subject": "Text", "body": "Text"}),
            (
                "/email/messages",
                {"recipient": "buyer@example.com", "subject": "Text", "body": "Text"},
            ),
        ]:
            assert client.post("/api/v1" + path, json=payload).status_code == 403


def test_browser_origin_contract_allows_frontend_and_rejects_cross_site(tmp_path: Path) -> None:
    app = create_app(
        Settings(database_url=SecretStr(f"sqlite:///{tmp_path}/origin.db"), environment="test")
    )
    with TestClient(app) as client:
        payload = {
            "name": "Owner",
            "company_name": "Org",
            "email": "origin@example.com",
            "password": "Origin-password123",
        }
        assert (
            client.post(
                "/api/v1/auth/signup", headers={"Origin": "http://localhost:3007"}, json=payload
            ).status_code
            == 201
        )
        response = client.post(
            "/api/v1/leads",
            headers={"Origin": "https://attacker.invalid"},
            json={"name": "Blocked"},
        )
        assert response.status_code == 403
        assert client.get("/api/v1/leads").json()["total"] == 0
