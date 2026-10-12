from datetime import date
from typing import Any

from fastapi import HTTPException
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from app.modules.crm.models import (
    Activity,
    Campaign,
    Contact,
    Deal,
    Lead,
    Party,
    Pipeline,
    Stage,
    Ticket,
)

MODELS = {
    "leads": Lead,
    "contacts": Contact,
    "parties": Party,
    "deals": Deal,
    "activities": Activity,
    "campaigns": Campaign,
    "tickets": Ticket,
    "pipelines": Pipeline,
}


class CRMRepository:
    def __init__(self, db: Session, user: Any):
        self.db, self.user = db, user

    def model(self, entity: str) -> Any:
        if entity not in MODELS:
            raise HTTPException(404, "Collection not found.")
        return MODELS[entity]

    def scope(self, model: Any, *, include_deleted: bool = False) -> Any:
        conditions = [model.org_id == self.user.org_id]
        if hasattr(model, "deleted_at") and not include_deleted:
            conditions.append(model.deleted_at.is_(None))
        if (
            self.user.role in {"Sales Rep", "Sales Representative"}
            and hasattr(model, "owner_id")
            and model not in {Pipeline}
        ):
            conditions.append(model.owner_id == self.user.id)
        return conditions

    def query(self, entity: str, *, include_deleted: bool = False) -> Any:
        model = self.model(entity)
        return select(model).where(*self.scope(model, include_deleted=include_deleted))

    def get(
        self, entity: str, record_id: str, lock: bool = False, *, include_deleted: bool = False
    ) -> Any:
        model = self.model(entity)
        query = self.query(entity, include_deleted=include_deleted).where(model.id == record_id)
        if lock:
            query = query.with_for_update()
        record = self.db.scalar(query)
        if record is None:
            raise HTTPException(404, "Record not found.")
        return record

    def stage(self, stage_id: str) -> Stage:
        result = self.db.scalar(
            select(Stage).where(Stage.id == stage_id, Stage.org_id == self.user.org_id)
        )
        if result is None:
            raise HTTPException(404, "Stage not found.")
        return result

    def list(
        self,
        entity: str,
        q: str = "",
        status: str | None = None,
        owner_id: str | None = None,
        stage_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
        sort: str = "updated_at",
        order: str = "desc",
        entity_type: str | None = None,
        entity_id: str | None = None,
        pipeline_id: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> tuple[list[Any], int]:
        model = self.model(entity)
        query = self.query(entity)
        if q:
            columns = [
                getattr(model, key)
                for key in ("name", "email", "phone", "company")
                if hasattr(model, key)
            ]
            escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            query = query.where(
                or_(*(column.ilike(f"%{escaped}%", escape="\\") for column in columns))
            )
        for key, value in (
            ("status", status),
            ("owner_id", owner_id),
            ("stage_id", stage_id),
            ("pipeline_id", pipeline_id),
            ("entity_type", entity_type),
            ("entity_id", entity_id),
        ):
            if value is not None:
                if not hasattr(model, key):
                    raise HTTPException(422, f"{key} is not a filter for this collection.")
                query = query.where(getattr(model, key) == value)
        if date_from or date_to:
            if entity != "activities":
                raise HTTPException(422, "Date-range filters apply to activities.")
            if date_from and date_to and date_from > date_to:
                raise HTTPException(422, "Start date must not follow end date.")
            day = activity_day()
            if date_from:
                query = query.where(day >= date_from.isoformat())
            if date_to:
                query = query.where(day <= date_to.isoformat())
        if sort not in {
            "name",
            "created_at",
            "updated_at",
            "amount",
            "value",
            "score",
            "due_date",
            "status",
            "expected_close_date",
            "budget",
        } or not hasattr(model, sort):
            raise HTTPException(422, "Choose a supported sort field.")
        count = self.db.scalar(select(func.count()).select_from(query.subquery())) or 0
        column = getattr(model, sort)
        query = (
            query.order_by(column.asc() if order == "asc" else column.desc(), model.id)
            .offset(offset)
            .limit(limit)
        )
        return list(self.db.scalars(query)), count


def activity_day() -> Any:
    """Date-only tasks keep their date; UTC timestamps display in Asia/Kolkata."""
    return case(
        (func.length(Activity.due_date) == 10, Activity.due_date),
        else_=func.date(Activity.due_date, "+5 hours", "+30 minutes"),
    )
