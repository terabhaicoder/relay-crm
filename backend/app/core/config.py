from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: Literal["development", "test", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    database_url: SecretStr = SecretStr("sqlite:///./erp.db")
    redis_url: SecretStr = SecretStr("redis://localhost:6379/0")
    celery_broker_url: SecretStr | None = None
    celery_result_backend: SecretStr | None = None
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3007",
            "http://127.0.0.1:3007",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    )
    session_days: int = Field(default=14, ge=1, le=90)
    signup_enabled: bool = True
    auth_ip_rate_limit: int = Field(default=300, ge=1, le=10000)
    auth_identity_rate_limit: int = Field(default=10, ge=1, le=100)
    demo_seed: bool = False
    demo_email: str = "owner@demo.local"
    demo_password: SecretStr | None = None
    upload_dir: Path = Path("./uploads")

    @model_validator(mode="after")
    def prevent_production_demo(self) -> "Settings":
        if self.environment == "production" and self.demo_seed:
            raise ValueError("Demo seed is available only in development or test environments.")
        if self.environment == "production":
            if not self.cors_origins or any(
                urlsplit(origin).scheme != "https"
                or urlsplit(origin).hostname in {"localhost", "127.0.0.1", "::1"}
                for origin in self.cors_origins
            ):
                raise ValueError("Production requires explicit public HTTPS CORS_ORIGINS.")
        return self

    @field_validator("database_url")
    @classmethod
    def require_async_postgresql(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().startswith(("postgresql+asyncpg://", "sqlite:///")):
            raise ValueError("DATABASE_URL must use postgresql+asyncpg or sqlite")
        return value

    @field_validator("redis_url", "celery_broker_url", "celery_result_backend")
    @classmethod
    def require_redis(cls, value: SecretStr | None) -> SecretStr | None:
        if value and not value.get_secret_value().startswith(("redis://", "rediss://")):
            raise ValueError("Redis connections must use redis:// or rediss://")
        return value

    @field_validator("cors_origins")
    @classmethod
    def explicit_origins(cls, value: list[str]) -> list[str]:
        normalized = []
        for origin in value:
            parsed = urlsplit(origin)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or parsed.username
                or parsed.password
                or parsed.query
                or parsed.fragment
                or parsed.path not in {"", "/"}
                or "*" in origin
            ):
                raise ValueError(
                    "CORS requires explicit HTTP(S) origins without paths or credentials"
                )
            normalized.append(origin.rstrip("/"))
        return normalized


@lru_cache
def get_settings() -> Settings:
    return Settings()
