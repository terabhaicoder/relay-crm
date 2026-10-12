import base64
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.main import create_app
from app.modules.files.models import Attachment


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    settings = Settings(
        database_url=SecretStr(f"sqlite:///{tmp_path}/files.db"),
        upload_dir=tmp_path / "uploads",
        environment="test",
    )
    with TestClient(create_app(settings), raise_server_exceptions=False) as http:
        response = http.post(
            "/api/v1/auth/signup",
            json={
                "name": "Owner",
                "company_name": "Files Company",
                "email": "owner@files.example",
                "password": "Files-password123",
            },
        )
        assert response.status_code == 201
        yield http


def upload(
    client: TestClient,
    lead_id: str,
    content: bytes,
    filename: str = "notes.txt",
    mime: str = "text/plain",
) -> Any:
    return client.post(
        "/api/v1/attachments",
        params={"entity_type": "leads", "entity_id": lead_id, "filename": filename},
        content=content,
        headers={"Content-Type": mime},
    )


def test_upload_download_delete_real_binary_file(client: TestClient) -> None:
    lead = client.post("/api/v1/leads", json={"name": "Customer file"}).json()
    image = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII="
    )
    response = upload(client, lead["id"], image, "company logo.png", "image/png")
    assert response.status_code == 201, response.text
    attachment = response.json()
    assert attachment["size_bytes"] == len(image)
    assert "storage_key" not in attachment
    assert (
        len(
            client.get(
                "/api/v1/attachments", params={"entity_type": "leads", "entity_id": lead["id"]}
            ).json()["items"]
        )
        == 1
    )
    download = client.get(f"/api/v1/attachments/{attachment['id']}/download")
    assert download.status_code == 200
    assert download.content == image
    assert "attachment;" in download.headers["content-disposition"]
    assert download.headers["cache-control"] == "private, no-store"
    assert client.delete(f"/api/v1/attachments/{attachment['id']}").status_code == 204
    assert client.get(f"/api/v1/attachments/{attachment['id']}/download").status_code == 404
    assert list(client.app.state.settings.upload_dir.iterdir()) == []


def test_attachment_tenant_and_own_visibility_and_readonly(client: TestClient) -> None:
    lead = client.post("/api/v1/leads", json={"name": "Owner-only file"}).json()
    file_id = upload(client, lead["id"], b"private notes").json()["id"]
    client.post(
        "/api/v1/team",
        json={
            "name": "Rep",
            "email": "rep@files.example",
            "password": "Rep-password123",
            "role": "Sales Rep",
        },
    )
    client.post(
        "/api/v1/auth/login", json={"email": "rep@files.example", "password": "Rep-password123"}
    )
    assert client.get(f"/api/v1/attachments/{file_id}/download").status_code == 404
    assert upload(client, lead["id"], b"forbidden").status_code == 404
    client.post(
        "/api/v1/auth/signup",
        json={
            "name": "Other",
            "company_name": "Other Company",
            "email": "other@files.example",
            "password": "Other-password123",
        },
    )
    assert client.get(f"/api/v1/attachments/{file_id}/download").status_code == 404
    assert client.delete(f"/api/v1/attachments/{file_id}").status_code == 404
    client.post(
        "/api/v1/auth/login", json={"email": "owner@files.example", "password": "Files-password123"}
    )
    client.post(
        "/api/v1/team",
        json={
            "name": "Reader",
            "email": "reader@files.example",
            "password": "Reader-password123",
            "role": "Read-only",
        },
    )
    client.post(
        "/api/v1/auth/login",
        json={"email": "reader@files.example", "password": "Reader-password123"},
    )
    assert client.get(f"/api/v1/attachments/{file_id}/download").status_code == 200
    assert upload(client, lead["id"], b"not allowed").status_code == 403
    assert client.delete(f"/api/v1/attachments/{file_id}").status_code == 403


def test_invalid_or_oversized_uploads_leave_no_files_or_metadata(client: TestClient) -> None:
    lead = client.post("/api/v1/leads", json={"name": "Validation"}).json()
    cases = [
        (b"not a PDF", "bad.pdf", "application/pdf", 422),
        (b"text", "../secret.txt", "text/plain", 422),
        (b"text", "script.exe", "application/octet-stream", 422),
        (b"a" * (10 * 1024 * 1024 + 1), "large.txt", "text/plain", 413),
    ]
    for content, filename, mime, status in cases:
        assert upload(client, lead["id"], content, filename, mime).status_code == status
    assert list(client.app.state.settings.upload_dir.iterdir()) == []
    with Session(client.app.state.engine) as db:
        assert db.scalar(select(func.count()).select_from(Attachment)) == 0


def test_failed_transaction_removes_uploaded_file(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.modules.files import router as file_routes

    lead = client.post("/api/v1/leads", json={"name": "Rollback"}).json()

    def fail(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("Test failure before transaction commit")

    monkeypatch.setattr(file_routes, "record_event", fail)
    response = upload(client, lead["id"], b"must be rolled back")
    assert response.status_code == 500
    assert "Test failure" not in response.text
    assert list(client.app.state.settings.upload_dir.iterdir()) == []
    with Session(client.app.state.engine) as db:
        assert db.scalar(select(func.count()).select_from(Attachment)) == 0


def test_upload_retry_uses_same_record_and_rejects_changed_content(client: TestClient) -> None:
    lead = client.post("/api/v1/leads", json={"name": "QA repeat file"}).json()
    params = {"entity_type": "leads", "entity_id": lead["id"], "filename": "qa.txt"}
    headers = {"Content-Type": "text/plain", "Idempotency-Key": "qa-attachment-1"}
    first = client.post("/api/v1/attachments", params=params, content=b"QA bytes", headers=headers)
    retry = client.post("/api/v1/attachments", params=params, content=b"QA bytes", headers=headers)
    assert first.status_code == retry.status_code == 201
    assert first.json() == retry.json()
    conflict = client.post(
        "/api/v1/attachments", params=params, content=b"Changed", headers=headers
    )
    assert conflict.status_code == 409
    renamed = client.post(
        "/api/v1/attachments",
        params={**params, "filename": "other.txt"},
        content=b"QA bytes",
        headers=headers,
    )
    assert renamed.status_code == 409
    assert len(list(client.app.state.settings.upload_dir.iterdir())) == 1
    with Session(client.app.state.engine) as db:
        assert db.scalar(select(func.count()).select_from(Attachment)) == 1
    assert client.delete(f"/api/v1/attachments/{first.json()['id']}").status_code == 204
    deleted_retry = client.post(
        "/api/v1/attachments",
        params=params,
        content=b"QA bytes",
        headers=headers,
    )
    assert deleted_retry.status_code == 404
    assert list(client.app.state.settings.upload_dir.iterdir()) == []


def test_upload_cached_result_rechecks_current_link_access(client: TestClient) -> None:
    from app.modules.auth.models import User
    from app.modules.crm.models import Lead

    lead = client.post("/api/v1/leads", json={"name": "QA moved file"}).json()
    params = {"entity_type": "leads", "entity_id": lead["id"], "filename": "qa.txt"}
    headers = {"Content-Type": "text/plain", "Idempotency-Key": "qa-attachment-visibility"}
    first = client.post("/api/v1/attachments", params=params, content=b"QA bytes", headers=headers)
    assert first.status_code == 201
    with Session(client.app.state.engine) as db:
        owner = db.scalar(select(User))
        assert owner is not None
        owner.role = "Sales Rep"
        linked = db.get(Lead, lead["id"])
        assert linked is not None
        linked.owner_id = None
        db.commit()
    retry = client.post("/api/v1/attachments", params=params, content=b"QA bytes", headers=headers)
    assert retry.status_code == 404
    assert len(list(client.app.state.settings.upload_dir.iterdir())) == 1


def test_simultaneous_upload_retries_persist_one_file(client: TestClient) -> None:
    from concurrent.futures import ThreadPoolExecutor

    lead = client.post("/api/v1/leads", json={"name": "QA concurrent file"}).json()

    def submit() -> Any:
        return client.post(
            "/api/v1/attachments",
            params={"entity_type": "leads", "entity_id": lead["id"], "filename": "qa.txt"},
            content=b"QA concurrent bytes",
            headers={"Content-Type": "text/plain", "Idempotency-Key": "qa-concurrent-file"},
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: submit(), range(2)))
    assert [response.status_code for response in responses] == [201, 201]
    assert responses[0].json()["id"] == responses[1].json()["id"]
    assert len(list(client.app.state.settings.upload_dir.iterdir())) == 1
    with Session(client.app.state.engine) as db:
        assert db.scalar(select(func.count()).select_from(Attachment)) == 1
