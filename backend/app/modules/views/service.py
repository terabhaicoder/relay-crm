from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.db import ensure_write_transaction
from app.modules.auth.models import User, utcnow
from app.modules.crm.repository import CRMRepository
from app.modules.crm.service import execute_idempotent, serialize
from app.modules.views.models import SavedView
from app.modules.views.repository import ViewRepository
from app.modules.views.schemas import ViewCreate, ViewFilters, ViewUpdate

STATUSES = {
    "leads": {"New", "Contacted", "Qualified", "Unqualified", "Converted"},
    "contacts": set(),
    "parties": set(),
    "deals": {"open", "won", "lost"},
    "activities": {"pending", "completed"},
    "campaigns": {"draft", "active", "completed", "paused"},
    "tickets": {"New", "Open", "Pending", "Resolved", "Closed"},
}


def validated_filters(db: Session, user: User, entity: str, filters: ViewFilters) -> dict[str, Any]:
    if entity not in STATUSES:
        raise HTTPException(422, "Choose a supported CRM collection.")
    if filters.status and filters.status not in STATUSES[entity]:
        raise HTTPException(422, "Choose a status supported by this collection.")
    parts = filters.sort.split(":")
    if len(parts) != 2 or parts[1] not in {"asc", "desc"}:
        raise HTTPException(422, "Choose a supported sort field and direction.")
    repo = CRMRepository(db, user)
    # Reuse the real list contract rather than accepting filters the UI cannot apply.
    repo.list(entity, sort=parts[0], order=parts[1], limit=1)
    if entity != "deals" and (filters.pipeline_id or filters.view):
        raise HTTPException(422, "Pipeline and board views are available for deals only.")
    if filters.pipeline_id:
        repo.get("pipelines", filters.pipeline_id)
    values = filters.model_dump(exclude_none=True)
    if not values.get("pipeline_id"):
        values.pop("pipeline_id", None)
    return values


def encode(row: SavedView) -> dict[str, Any]:
    value = serialize(row)
    return {
        key: value[key]
        for key in ("id", "entity", "name", "filters", "version", "created_at", "updated_at")
    }


def listing(db: Session, user: User, entity: str, limit: int, offset: int) -> dict[str, Any]:
    query = ViewRepository(db, user).query().where(SavedView.entity == entity)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(query.order_by(SavedView.name, SavedView.id).offset(offset).limit(limit))
    return {"items": [encode(row) for row in rows], "total": total}


def create(db: Session, user: User, payload: ViewCreate, key: str) -> dict[str, Any]:
    values = validated_filters(db, user, payload.entity, payload.filters)

    def create_response() -> dict[str, Any]:
        row = SavedView(
            org_id=user.org_id,
            user_id=user.id,
            entity=payload.entity,
            name=payload.name,
            filters=values,
            created_by=user.id,
            updated_by=user.id,
        )
        db.add(row)
        db.flush()
        return encode(row)

    return execute_idempotent(
        db,
        user,
        key,
        f"{user.id}/saved-views",
        payload.model_dump(),
        create_response,
        lambda old: encode(ViewRepository(db, user).get(old["id"])),
    )


def update(db: Session, user: User, record_id: str, payload: ViewUpdate) -> dict[str, Any]:
    ensure_write_transaction(db)
    row = ViewRepository(db, user).get(record_id)
    if row.version != payload.version:
        raise HTTPException(409, "This saved view changed. Refresh before saving it again.")
    row.filters = validated_filters(db, user, row.entity, payload.filters)
    row.name = payload.name
    row.version += 1
    row.updated_at = utcnow()
    row.updated_by = user.id
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "A saved view with this name already exists.") from None
    return encode(row)


def remove(db: Session, user: User, record_id: str) -> None:
    ensure_write_transaction(db)
    db.delete(ViewRepository(db, user).get(record_id))
    db.commit()
