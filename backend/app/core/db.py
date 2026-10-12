import sqlite3
from collections.abc import Iterator
from decimal import Decimal
from typing import Annotated

from fastapi import Request
from sqlalchemy import Engine, MetaData, Numeric, create_engine, event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, mapped_column

from app.core.config import Settings

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

# Shared exact-decimal column types. Business models arrive after Phase 0 approval.
Money = Annotated[Decimal, mapped_column(Numeric(18, 2))]
Quantity = Annotated[Decimal, mapped_column(Numeric(18, 3))]
Rate = Annotated[Decimal, mapped_column(Numeric(18, 4))]


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def build_engine(settings: Settings) -> AsyncEngine:
    return create_async_engine(
        settings.database_url.get_secret_value(),
        pool_pre_ping=True,
        hide_parameters=True,
        connect_args={"server_settings": {"timezone": "UTC"}, "timeout": 3},
    )


def build_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    # Services explicitly use `async with session.begin()` for multi-table writes.
    return async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


def build_local_engine(settings: Settings) -> Engine:
    url = settings.database_url.get_secret_value()
    if not url.startswith("sqlite:///"):
        raise ValueError("The runnable CRM profile currently requires a SQLite DATABASE_URL.")
    engine = create_engine(
        url, connect_args={"check_same_thread": False, "timeout": 20}, hide_parameters=True
    )

    @event.listens_for(engine, "connect")
    def sqlite_constraints(connection: object, record: object) -> None:
        cursor = connection.cursor()  # type: ignore[attr-defined]
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

    return engine


def get_session(request: Request) -> Iterator[Session]:
    with Session(request.app.state.engine, expire_on_commit=False) as session:
        try:
            yield session
        except Exception:
            session.rollback()
            raise


def ensure_write_transaction(session: Session) -> None:
    """Begin SQLite's real outer transaction before any nested savepoints.

    The legacy sqlite3 driver does not start a transaction for SAVEPOINT, so
    releasing the first savepoint would otherwise commit data prematurely.
    Call once before a multi-row writer; ordinary read requests remain unchanged.
    """
    connection = session.connection()
    if connection.dialect.name == "sqlite":
        driver = connection.connection.driver_connection
        if isinstance(driver, sqlite3.Connection) and not driver.in_transaction:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
