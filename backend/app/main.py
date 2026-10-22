import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import Engine, text
from sqlalchemy.orm import sessionmaker
from starlette.middleware.base import RequestResponseEndpoint

from app.core.bootstrap import initialize_database
from app.core.config import Settings, get_settings
from app.core.db import build_local_engine
from app.core.errors import error_response, install_error_handlers
from app.core.limits import BodyLimitMiddleware, RateLimiter
from app.core.logging import configure_logging
from app.health.router import router as health_router
from app.modules.auth.router import router as auth_router
from app.modules.commercial.router import router as commercial_router
from app.modules.crm.reporting_router import router as reporting_router
from app.modules.crm.router import router as crm_router
from app.modules.customization.router import router as customization_router
from app.modules.engagement.router import router as engagement_router
from app.modules.engagement.workflows import worker_loop
from app.modules.files.router import router as files_router
from app.modules.intake.router import router as intake_router
from app.modules.views.router import router as views_router

logger = logging.getLogger(__name__)


class LocalDatabaseProbe:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    async def check(self) -> dict[str, bool]:
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return {"database": True}
        except Exception:
            return {"database": False}


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        configure_logging(config.log_level)
        engine = build_local_engine(config)
        initialize_database(engine, config)
        app.state.engine = engine
        app.state.settings = config
        app.state.probe = LocalDatabaseProbe(engine)
        stop_worker = asyncio.Event()
        worker = (
            asyncio.create_task(
                worker_loop(sessionmaker(bind=engine, expire_on_commit=False), stop_worker)
            )
            if config.environment != "test"
            else None
        )
        try:
            yield
        finally:
            stop_worker.set()
            if worker:
                await worker
            engine.dispose()

    app = FastAPI(
        title="Relay CRM",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/api/v1/docs" if config.environment != "production" else None,
        redoc_url=None,
        openapi_url="/api/v1/openapi.json",
    )
    app.state.settings = config
    app.state.auth_limiter = RateLimiter()
    app.state.intake_limiter = RateLimiter()
    app.add_middleware(BodyLimitMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "Idempotency-Key", "X-CSRF-Token"],
    )

    @app.middleware("http")
    async def request_metadata(request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method in {"POST", "PATCH", "PUT", "DELETE"}:
            origin = request.headers.get("origin")
            same_origin = f"{request.url.scheme}://{request.url.netloc}"
            if origin and origin not in {*config.cors_origins, same_origin}:
                return error_response(
                    403, "ORIGIN_NOT_ALLOWED", "This request origin is not allowed."
                )
            if request.headers.get("sec-fetch-site") == "cross-site" and not origin:
                return error_response(
                    403, "ORIGIN_NOT_ALLOWED", "This request origin is not allowed."
                )
        if request.method == "POST" and request.url.path.startswith("/api/v1/auth/"):
            key = request.client.host if request.client else "unknown"
            if not app.state.auth_limiter.allow("peer:" + key, config.auth_ip_rate_limit):
                limited = error_response(
                    429, "RATE_LIMITED", "Too many attempts. Please wait one minute."
                )
                limited.headers["Retry-After"] = "60"
                return limited
        # Generate our own ID; untrusted header text must not enter operational logs.
        request_id = str(uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers.setdefault("Cache-Control", "no-store")
        response.headers["Referrer-Policy"] = "no-referrer"
        logger.info(
            "http_request",
            extra={
                "safe_event": "http_request",
                "request_id": request_id,
                "status_code": response.status_code,
            },
        )
        return response

    install_error_handlers(app)
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(engagement_router, prefix="/api/v1")
    app.include_router(files_router, prefix="/api/v1")
    app.include_router(reporting_router, prefix="/api/v1")
    app.include_router(commercial_router, prefix="/api/v1")
    app.include_router(views_router, prefix="/api/v1")
    app.include_router(customization_router, prefix="/api/v1")
    app.include_router(intake_router, prefix="/api/v1")
    app.include_router(crm_router, prefix="/api/v1")
    return app
