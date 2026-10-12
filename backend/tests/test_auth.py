from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.main import create_app
from app.modules.auth.models import LoginSession, User
from app.modules.auth.service import verify_password


@pytest.fixture
def client(tmp_path: Path):
    app = create_app(
        Settings(database_url=SecretStr(f"sqlite:///{tmp_path}/crm.db"), environment="test")
    )
    with TestClient(app) as http:
        yield http


def signup(client: TestClient, email: str = "owner@example.com"):
    return client.post(
        "/api/v1/auth/signup",
        json={
            "name": "Aditi Sharma",
            "company_name": "Test Company",
            "email": email,
            "password": "Test-pass-234!",
        },
    )


def test_signup_login_logout_persist_and_revoke_real_sessions(client: TestClient) -> None:
    response = signup(client)
    assert response.status_code == 201, response.text
    assert response.json()["role"] == "Owner"
    assert response.json()["company_name"] == "Test Company"
    assert "password" not in response.text
    assert "HttpOnly" in response.headers["set-cookie"]
    assert client.get("/api/v1/me").status_code == 200
    with Session(client.app.state.engine) as db:
        user = db.scalar(select(User))
        assert user is not None
        assert user.password_hash != "Test-pass-234!"
        assert verify_password("Test-pass-234!", user.password_hash)
        assert db.scalar(select(LoginSession)) is not None
    assert client.post("/api/v1/auth/logout").status_code == 204
    assert client.get("/api/v1/me").status_code == 401
    assert (
        client.post(
            "/api/v1/auth/login", json={"email": "owner@example.com", "password": "wrong"}
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/v1/auth/login", json={"email": "owner@example.com", "password": "Test-pass-234!"}
        ).status_code
        == 200
    )
    assert client.get("/api/v1/me").json()["name"] == "Aditi Sharma"


def test_duplicate_signup_is_atomic(client: TestClient) -> None:
    assert signup(client).status_code == 201
    duplicate = signup(client)
    assert duplicate.status_code == 409
    assert "already registered" in duplicate.json()["error"]["message"]
    with Session(client.app.state.engine) as db:
        assert len(list(db.scalars(select(User)))) == 1


def test_forged_cookie_and_cross_site_write_rejected(client: TestClient) -> None:
    client.cookies.set("erp_session", "forged-token")
    assert client.get("/api/v1/me").status_code == 401
    response = client.post(
        "/api/v1/auth/signup",
        headers={"Origin": "https://evil.example"},
        json={
            "name": "No",
            "email": "bad@example.com",
            "password": "Test123456",
            "company_name": "No",
        },
    )
    assert response.status_code == 403


def test_ready_checks_real_sqlite(client: TestClient) -> None:
    assert client.get("/api/v1/health/ready").status_code == 200


def test_different_signups_get_different_tenants(client: TestClient) -> None:
    first = signup(client).json()
    second = signup(client, "other@example.com").json()
    assert first["org_id"] != second["org_id"]


def test_owner_adds_team_member_and_rep_cannot_add_another(client: TestClient) -> None:
    owner = signup(client).json()
    response = client.post(
        "/api/v1/team",
        json={
            "name": "Sales Rep",
            "email": "rep@example.com",
            "password": "Rep-password123",
            "role": "Sales Rep",
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["org_id"] == owner["org_id"]
    assert len(client.get("/api/v1/team").json()) == 2
    client.post("/api/v1/auth/logout")
    assert (
        client.post(
            "/api/v1/auth/login", json={"email": "rep@example.com", "password": "Rep-password123"}
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/v1/team",
            json={
                "name": "Other",
                "email": "other@example.com",
                "password": "Other-password123",
                "role": "Admin",
            },
        ).status_code
        == 403
    )


def test_password_change_revokes_old_sessions(client: TestClient) -> None:
    signup(client)
    old_token = client.cookies.get("erp_session")
    response = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "Test-pass-234!", "new_password": "New-password567!"},
    )
    assert response.status_code == 200
    assert client.cookies.get("erp_session") != old_token
    assert (
        client.get("/api/v1/me", headers={"Cookie": f"erp_session={old_token}"}).status_code == 401
    )
    assert client.get("/api/v1/me").status_code == 200


def test_invite_acceptance_is_single_use_and_uses_inviting_tenant(client: TestClient) -> None:
    owner = signup(client).json()
    invite = client.post(
        "/api/v1/team/invites", json={"email": "invited@example.com", "role": "Read-only"}
    )
    assert invite.status_code == 201, invite.text
    token = invite.json()["token"]
    assert invite.json()["delivery"] == "manual"
    assert client.get(f"/api/v1/auth/invites/{token}").json()["company_name"] == "Test Company"
    accepted = client.post(
        "/api/v1/auth/accept-invite",
        json={"token": token, "name": "Invited Person", "password": "Invitation123!"},
    )
    assert accepted.status_code == 201, accepted.text
    assert accepted.json()["org_id"] == owner["org_id"]
    assert accepted.json()["role"] == "Read-only"
    assert (
        client.post(
            "/api/v1/auth/accept-invite",
            json={"token": token, "name": "Again", "password": "Invitation123!"},
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/api/v1/team/invites", json={"email": "another@example.com", "role": "Admin"}
        ).status_code
        == 403
    )


def test_active_sessions_are_scoped_and_revocable(client: TestClient) -> None:
    signup(client)
    sessions = client.get("/api/v1/auth/sessions").json()
    assert len(sessions) == 1
    assert sessions[0]["current"] is True
    assert sessions[0]["created_at"].endswith("+00:00")
    assert sessions[0]["expires_at"].endswith("+00:00")
    session_id = sessions[0]["id"]
    signup(client, "other-owner@example.com")
    assert client.delete(f"/api/v1/auth/sessions/{session_id}").status_code == 404
    own_id = client.get("/api/v1/auth/sessions").json()[0]["id"]
    assert client.delete(f"/api/v1/auth/sessions/{own_id}").status_code == 204
    assert client.get("/api/v1/me").status_code == 401
