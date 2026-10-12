import hashlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.bootstrap_owner import bootstrap_owner
from app.core.config import Settings
from app.core.limits import RateLimiter
from app.main import create_app
from app.modules.auth.models import SecurityAudit, User
from app.modules.auth.schemas import SignupRequest
from app.reset_password import reset_password


def config(tmp_path: Path, **overrides: object) -> Settings:
    return Settings(
        database_url=SecretStr(f"sqlite:///{tmp_path}/security.db"),
        upload_dir=tmp_path / "files",
        **overrides,
    )


@pytest.mark.parametrize(
    "origins", [["http://crm.example.com"], ["https://localhost"], ["https://127.0.0.1"], []]
)
def test_production_rejects_insecure_origins(origins: list[str]) -> None:
    with pytest.raises(ValidationError, match="public HTTPS"):
        Settings(environment="production", cors_origins=origins)


def test_closed_signup_bootstrap_and_secure_cookie(tmp_path: Path) -> None:
    settings = config(
        tmp_path,
        environment="production",
        cors_origins=["https://crm.example.com"],
        signup_enabled=False,
    )
    payload = SignupRequest(
        name="Owner",
        email="owner@example.com",
        company_name="Live company",
        password="Secure-owner123!",
    )
    bootstrap_owner(settings, payload)
    with pytest.raises(ValueError, match="already exists"):
        bootstrap_owner(settings, payload)
    with TestClient(create_app(settings), base_url="https://crm.example.com") as client:
        assert client.get("/api/v1/auth/options").json() == {"signup_enabled": False}
        assert client.post("/api/v1/auth/signup", json=payload.model_dump()).status_code == 403
        response = client.post(
            "/api/v1/auth/login", json={"email": payload.email, "password": payload.password}
        )
        assert response.status_code == 200
        assert "Secure" in response.headers["set-cookie"]
        assert "HttpOnly" in response.headers["set-cookie"]
        assert response.headers["cache-control"] == "no-store"
        assert client.get("/api/v1/me").status_code == 200


def test_account_throttle_ignores_forged_forwarded_ips(tmp_path: Path) -> None:
    with TestClient(create_app(config(tmp_path, auth_identity_rate_limit=2))) as client:
        for index in range(2):
            response = client.post(
                "/api/v1/auth/login",
                headers={"X-Forwarded-For": f"192.0.2.{index}"},
                json={"email": "victim@example.com", "password": "wrong"},
            )
            assert response.status_code == 401
        response = client.post(
            "/api/v1/auth/login",
            headers={"X-Forwarded-For": "192.0.2.99"},
            json={"email": "VICTIM@example.com", "password": "wrong"},
        )
        assert response.status_code == 429
        assert response.headers["retry-after"] == "60"
        other = client.post(
            "/api/v1/auth/login", json={"email": "different@example.com", "password": "wrong"}
        )
        assert other.status_code == 401


def test_rate_limiter_storage_is_bounded_and_does_not_keep_plaintext_identity() -> None:
    limiter = RateLimiter(max_keys=5)
    for index in range(20):
        assert limiter.allow(f"person{index}@example.com", 2)
    assert len(limiter.buckets) == 5
    assert all("@" not in key for key in limiter.buckets)


def test_request_size_is_checked_even_without_content_length(tmp_path: Path) -> None:
    with TestClient(create_app(config(tmp_path))) as client:
        response = client.post(
            "/api/v1/auth/login",
            content=iter([b"x" * 9000, b"y" * 9000]),
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 413, response.text
        assert response.json()["error"]["code"] == "REQUEST_TOO_LARGE"


def test_old_password_hash_upgrades_and_deactivated_member_can_be_reenabled(tmp_path: Path) -> None:
    with TestClient(create_app(config(tmp_path))) as client:
        payload = {
            "name": "Owner",
            "company_name": "Company",
            "email": "owner@example.com",
            "password": "Owner-password123",
        }
        assert client.post("/api/v1/auth/signup", json=payload).status_code == 201
        member = client.post(
            "/api/v1/team",
            json={
                "name": "Sales",
                "email": "sales@example.com",
                "password": "Sales-password123",
                "role": "Sales Rep",
            },
        ).json()
        client.patch(f"/api/v1/team/{member['id']}", json={"is_active": False})
        roster = client.get("/api/v1/team").json()
        assert next(row for row in roster if row["id"] == member["id"])["is_active"] is False
        assert (
            client.patch(f"/api/v1/team/{member['id']}", json={"is_active": True}).json()[
                "is_active"
            ]
            is True
        )
        salt = "00" * 16
        old_hash = (
            "scrypt$"
            + salt
            + "$"
            + hashlib.scrypt(
                payload["password"].encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1
            ).hex()
        )
        with Session(client.app.state.engine) as session:
            user = session.scalar(select(User).where(User.email == payload["email"]))
            assert user is not None
            user.password_hash = old_hash
            session.commit()
        assert (
            client.post(
                "/api/v1/auth/login",
                json={"email": payload["email"], "password": payload["password"]},
            ).status_code
            == 200
        )
        with Session(client.app.state.engine) as session:
            user = session.scalar(select(User).where(User.email == payload["email"]))
            assert user is not None and user.password_hash.startswith("scrypt-v2$")


def test_operator_reset_revokes_sessions_and_records_operator_action(tmp_path: Path) -> None:
    settings = config(tmp_path)
    with TestClient(create_app(settings)) as client:
        payload = {
            "name": "Owner",
            "company_name": "Company",
            "email": "owner@example.com",
            "password": "Old-password123",
        }
        assert client.post("/api/v1/auth/signup", json=payload).status_code == 201
        reset_password(settings, payload["email"], "New-password456")
        assert client.get("/api/v1/me").status_code == 401
        assert (
            client.post(
                "/api/v1/auth/login",
                json={"email": payload["email"], "password": payload["password"]},
            ).status_code
            == 401
        )
        assert (
            client.post(
                "/api/v1/auth/login",
                json={"email": payload["email"], "password": "New-password456"},
            ).status_code
            == 200
        )
        with Session(client.app.state.engine) as session:
            assert (
                session.scalar(
                    select(SecurityAudit).where(
                        SecurityAudit.action.startswith("operator_password_reset_uid_")
                    )
                )
                is not None
            )


def test_automation_history_respects_sales_rep_record_visibility(tmp_path: Path) -> None:
    with TestClient(create_app(config(tmp_path))) as client:
        client.post(
            "/api/v1/auth/signup",
            json={
                "name": "Owner",
                "company_name": "Company",
                "email": "owner@example.com",
                "password": "Owner-password123",
            },
        )
        rule = {
            "name": "Follow up",
            "trigger": "leads.created",
            "action": "notify",
            "action_text": "Contact {{name}}",
        }
        assert client.post("/api/v1/automations", json=rule).status_code == 201
        private = client.post("/api/v1/leads", json={"name": "Private lead"}).json()
        client.post(
            "/api/v1/team",
            json={
                "name": "Rep",
                "email": "rep@example.com",
                "password": "Rep-password123",
                "role": "Sales Rep",
            },
        )
        client.post(
            "/api/v1/auth/login", json={"email": "rep@example.com", "password": "Rep-password123"}
        )
        own = client.post("/api/v1/leads", json={"name": "My lead"}).json()
        runs = client.get("/api/v1/automations/runs").json()["items"]
        assert {run["entity_id"] for run in runs} == {own["id"]}
        assert private["id"] not in str(runs)
