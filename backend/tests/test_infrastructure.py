import os

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.core.config import Settings
from app.core.db import build_engine
from app.main import create_app

pytestmark = pytest.mark.integration


async def test_migrated_postgres_and_redis_are_really_ready() -> None:
    # Explicit integration runs fail with setup instructions rather than silently skipping.
    assert os.getenv("DATABASE_URL"), "Set DATABASE_URL and run alembic upgrade head first."
    assert os.getenv("REDIS_URL"), "Set REDIS_URL to the real test Redis instance."
    settings = Settings()
    engine = build_engine(settings)
    try:
        async with engine.connect() as connection:
            extensions = await connection.execute(
                text("SELECT extname FROM pg_extension WHERE extname IN ('pg_trgm', 'vector')")
            )
            assert set(extensions.scalars()) == {"pg_trgm", "vector"}
            revision = await connection.scalar(text("SELECT version_num FROM alembic_version"))
            assert revision == "0001_database_extensions"
    finally:
        await engine.dispose()
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/health/ready")
    assert response.status_code == 200
