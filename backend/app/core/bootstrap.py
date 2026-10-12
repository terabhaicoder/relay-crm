import hashlib
import sqlite3
from pathlib import Path

from sqlalchemy import Engine, select, text
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.modules.auth.models import Org, User
from app.modules.auth.schemas import SignupRequest
from app.modules.auth.service import create_account


def initialize_database(engine: Engine, settings: Settings) -> None:
    """Apply numbered, checksummed SQLite migrations, then optional explicit demo seed."""
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE IF NOT EXISTS crm_schema_migrations "
                "(version VARCHAR(100) PRIMARY KEY, checksum VARCHAR(64) NOT NULL, "
                "applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
            )
        )
    migrations = Path(__file__).resolve().parents[2] / "local_migrations"
    migration_paths = sorted(migrations.glob("*.sql"))
    if not migration_paths:
        raise RuntimeError("Local database migrations are missing from this installation.")
    for path in migration_paths:
        sql = path.read_text()
        checksum = hashlib.sha256(sql.encode()).hexdigest()
        with engine.begin() as connection:
            applied = connection.execute(
                text("SELECT checksum FROM crm_schema_migrations WHERE version=:version"),
                {"version": path.stem},
            ).scalar_one_or_none()
            if applied is not None:
                if applied != checksum:
                    raise RuntimeError(f"Applied migration {path.stem} was modified.")
                continue
            statement = ""
            for line in sql.splitlines(keepends=True):
                statement += line
                if sqlite3.complete_statement(statement):
                    connection.exec_driver_sql(statement)
                    statement = ""
            if statement.strip():
                raise RuntimeError(f"Migration {path.stem} contains an incomplete SQL statement.")
            connection.execute(
                text(
                    "INSERT INTO crm_schema_migrations(version,checksum) "
                    "VALUES (:version,:checksum)"
                ),
                {"version": path.stem, "checksum": checksum},
            )
    if settings.demo_seed:
        if not settings.demo_password or len(settings.demo_password.get_secret_value()) < 8:
            raise ValueError("DEMO_SEED requires DEMO_PASSWORD with at least 8 characters.")
        with Session(engine) as db:
            user = db.scalar(select(User).where(User.email == settings.demo_email))
            if user is not None:
                org = db.get(Org, user.org_id)
                if org is None or org.name != "Relay Demo Workspace":
                    raise ValueError(
                        "Demo seed cannot add sample data to an existing real workspace."
                    )
            if user is None:
                user = create_account(
                    db,
                    SignupRequest(
                        name="Demo Owner",
                        company_name="Relay Demo Workspace",
                        email=settings.demo_email,
                        password=settings.demo_password.get_secret_value(),
                    ),
                )
            from app.modules.crm.seed import seed_demo

            seed_demo(db, user)
            db.commit()
