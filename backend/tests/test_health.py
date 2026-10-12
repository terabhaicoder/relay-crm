import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.health.router import get_probe
from app.main import create_app


class Probe:
    """Unit-test dependency double; never part of the runtime application."""

    def __init__(self, database: bool, redis: bool) -> None:
        self.database = database
        self.redis = redis

    async def check(self) -> dict[str, bool]:
        return {"database": self.database, "redis": self.redis}


async def test_liveness_does_not_claim_dependency_readiness(settings: Settings) -> None:
    app = create_app(settings)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["x-request-id"]
    assert response.headers["x-content-type-options"] == "nosniff"


@pytest.mark.parametrize("database,redis", [(False, True), (True, False), (False, False)])
async def test_readiness_fails_when_any_dependency_is_down(
    settings: Settings, database: bool, redis: bool
) -> None:
    app = create_app(settings)
    app.dependency_overrides[get_probe] = lambda: Probe(database, redis)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/health/ready")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "DEPENDENCY_UNAVAILABLE"
    assert "postgresql" not in response.text


async def test_readiness_succeeds_only_after_probe_confirmation(settings: Settings) -> None:
    app = create_app(settings)
    app.dependency_overrides[get_probe] = lambda: Probe(True, True)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_not_found_has_standard_safe_error(settings: Settings) -> None:
    app = create_app(settings)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/does-not-exist")
    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "NOT_FOUND",
            "message": "The requested record was not found.",
            "details": {},
        }
    }


def test_openapi_exposes_error_contract(settings: Settings) -> None:
    schema = create_app(settings).openapi()
    assert "503" in schema["paths"]["/api/v1/health/ready"]["get"]["responses"]
    assert set(schema["components"]["schemas"]["ErrorBody"]["required"]) == {"code", "message"}
