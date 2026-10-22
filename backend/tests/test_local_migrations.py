import shutil
from pathlib import Path

import pytest
from pydantic import SecretStr
from sqlalchemy import func, inspect, select, text
from sqlalchemy.orm import Session

from app.core import bootstrap
from app.core.bootstrap import initialize_database
from app.core.config import Settings
from app.core.db import Base, build_local_engine
from app.main import create_app
from app.modules.crm.models import Lead


def test_local_migrations_apply_once_and_match_registered_schema(tmp_path: Path) -> None:
    settings = Settings(database_url=SecretStr(f"sqlite:///{tmp_path}/migrations.db"))
    create_app(settings)
    engine = build_local_engine(settings)
    try:
        initialize_database(engine, settings)
        initialize_database(engine, settings)
        inspector = inspect(engine)
        for table in Base.metadata.sorted_tables:
            assert inspector.has_table(table.name), table.name
            actual = {column["name"] for column in inspector.get_columns(table.name)}
            assert actual == set(table.c.keys()), table.name
        with engine.connect() as connection:
            migrations = Path(bootstrap.__file__).resolve().parents[2] / "local_migrations"
            assert connection.scalar(text("SELECT count(*) FROM crm_schema_migrations")) == len(
                list(migrations.glob("*.sql"))
            )
    finally:
        engine.dispose()


def test_demo_seed_is_explicit_and_idempotent(tmp_path: Path) -> None:
    settings = Settings(
        database_url=SecretStr(f"sqlite:///{tmp_path}/demo.db"),
        environment="test",
        demo_seed=True,
        demo_password=SecretStr("Demo-test123!"),
    )
    engine = build_local_engine(settings)
    try:
        initialize_database(engine, settings)
        with Session(engine) as db:
            first = db.scalar(select(func.count()).select_from(Lead))
        assert first and first > 0
        initialize_database(engine, settings)
        with Session(engine) as db:
            assert db.scalar(select(func.count()).select_from(Lead)) == first
    finally:
        engine.dispose()


def test_changing_an_applied_migration_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = Path(bootstrap.__file__).resolve().parents[2] / "local_migrations"
    local_root = tmp_path / "installation"
    copied = local_root / "local_migrations"
    shutil.copytree(source, copied)
    monkeypatch.setattr(bootstrap, "__file__", str(local_root / "app" / "core" / "bootstrap.py"))
    settings = Settings(database_url=SecretStr(f"sqlite:///{tmp_path}/immutable.db"))
    engine = build_local_engine(settings)
    try:
        initialize_database(engine, settings)
        path = copied / "0001_auth.sql"
        path.write_text(path.read_text() + "\n-- changed after application\n")
        with pytest.raises(RuntimeError, match="was modified"):
            initialize_database(engine, settings)
    finally:
        engine.dispose()
