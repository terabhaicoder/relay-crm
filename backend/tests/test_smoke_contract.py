import importlib.util
from pathlib import Path
from typing import Any
from urllib.error import HTTPError

from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.config import Settings
from app.main import create_app


def test_deployment_smoke_contract_against_real_database(tmp_path: Path) -> None:
    script = Path(__file__).resolve().parents[2] / "scripts" / "smoke.py"
    spec = importlib.util.spec_from_file_location("deployment_smoke", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    config = Settings(
        database_url=SecretStr(f"sqlite:///{tmp_path}/smoke.db"),
        upload_dir=tmp_path / "uploads",
        environment="test",
    )
    with TestClient(create_app(config)) as client:

        def call(method: str, path: str, payload: Any = None, raw: bytes | None = None) -> Any:
            response = client.request(
                method,
                "/api/v1" + path,
                json=payload,
                content=raw,
                headers={"Content-Type": "text/plain"} if raw is not None else {},
            )
            if response.status_code >= 400:
                raise HTTPError(
                    str(response.url), response.status_code, response.reason_phrase, {}, None
                )
            if response.content and "application/json" in response.headers.get("content-type", ""):
                return response.json()
            return response.content

        module.exercise(call)
