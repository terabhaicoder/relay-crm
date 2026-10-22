from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from app.modules.auth.models import User
from app.modules.engagement.models import (
    Automation,
    AutomationJob,
    AutomationRun,
    EmailDraft,
    EmailTemplate,
    Notification,
)


def create_engagement(
    db: Session,
    user: User,
    entity: str,
    payload: dict[str, Any],
    idempotency_key: str | None,
) -> dict[str, Any]:
    from app.core.auth import require_write
    from app.modules.crm.repository import CRMRepository
    from app.modules.crm.service import execute_idempotent

    require_write(user)
    if entity == "automations" and user.role not in {"Owner", "Admin", "Sales Manager"}:
        raise HTTPException(403, "Only managers can configure automations.")
    model: Any = {
        "automations": Automation,
        "email/messages": EmailDraft,
        "email/templates": EmailTemplate,
    }[entity]

    def validate_link(values: dict[str, Any]) -> None:
        if values.get("entity_type") or values.get("entity_id"):
            if not values.get("entity_type") or not values.get("entity_id"):
                raise HTTPException(422, "Choose a valid linked record.")
            CRMRepository(db, user).get(values["entity_type"], values["entity_id"])

    def response(row: Any) -> dict[str, Any]:
        return {
            column.name: jsonable_encoder(getattr(row, column.name))
            for column in row.__table__.columns
        }

    def replay(previous: dict[str, Any]) -> dict[str, Any]:
        row = db.scalar(
            select(model).where(model.org_id == user.org_id, model.id == previous["id"])
        )
        if row is None or (
            model is EmailDraft
            and user.role in {"Sales Rep", "Sales Representative"}
            and row.owner_id != user.id
        ):
            raise HTTPException(404, "Record not found.")
        if model is EmailDraft:
            validate_link(response(row))
        return response(row)

    def create_response() -> dict[str, Any]:
        values = {**payload}
        if model in {Automation, EmailDraft}:
            values["owner_id"] = user.id
        if model is EmailDraft:
            validate_link(values)
        if model is Automation:
            from app.modules.engagement.workflows import validate_targets

            validate_targets(db, user, values.get("steps", []))
        row = model(org_id=user.org_id, **values)
        db.add(row)
        db.flush()
        return response(row)

    return execute_idempotent(
        db, user, idempotency_key, f"{user.id}/{entity}", payload, create_response, replay
    )


def list_engagement(
    db: Session,
    user: User,
    entity: str,
    *,
    q: str = "",
    sort: str = "created_at",
    order: str = "desc",
    limit: int = 50,
    offset: int = 0,
    entity_type: str | None = None,
    entity_id: str | None = None,
    enabled: bool | None = None,
) -> dict[str, Any]:
    model: Any = Automation if entity == "automations" else EmailDraft
    query = select(model).where(model.org_id == user.org_id)
    if model is Automation and enabled is not None:
        query = query.where(model.enabled == enabled)
    if model is EmailDraft and user.role in {"Sales Rep", "Sales Representative"}:
        query = query.where(model.owner_id == user.id)
    if entity_type or entity_id:
        from app.modules.crm.repository import CRMRepository

        if model is not EmailDraft or not entity_type or not entity_id:
            raise HTTPException(422, "Choose a related record type and record ID together.")
        CRMRepository(db, user).get(entity_type, entity_id)
        query = query.where(model.entity_type == entity_type, model.entity_id == entity_id)
    if q:
        escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        fields = (
            ("name", "trigger", "action_text")
            if model is Automation
            else ("subject", "recipient", "body")
        )
        query = query.where(
            or_(*(getattr(model, field).ilike(f"%{escaped}%", escape="\\") for field in fields))
        )
    if sort == "name" and model is EmailDraft:
        sort = "subject"
    if sort not in {"name", "subject", "created_at"} or not hasattr(model, sort):
        raise HTTPException(422, "Choose name or created_at as the sort field.")
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    column = getattr(model, sort)
    records = db.scalars(
        query.order_by(column.asc() if order == "asc" else column.desc(), model.id)
        .offset(offset)
        .limit(limit)
    )
    return {
        "items": [
            {column.name: getattr(record, column.name) for column in record.__table__.columns}
            for record in records
        ],
        "total": total,
        "page": offset // limit + 1,
        "page_size": limit,
    }


def relink_entity(
    db: Session, user: User, entity_type: str, source_id: str, target_id: str
) -> None:
    """Preserve communications and notifications inside an authorized merge transaction."""
    from app.modules.crm.repository import CRMRepository

    repository = CRMRepository(db, user)
    repository.get(entity_type, source_id)
    repository.get(entity_type, target_id)
    for model in (EmailDraft, Notification, AutomationRun, AutomationJob):
        db.execute(
            update(model)
            .where(
                model.org_id == user.org_id,
                model.entity_type == entity_type,
                model.entity_id == source_id,
            )
            .values(entity_id=target_id)
        )
    db.execute(
        update(AutomationJob)
        .where(
            AutomationJob.org_id == user.org_id,
            AutomationJob.result_entity_type == entity_type,
            AutomationJob.result_entity_id == source_id,
        )
        .values(result_entity_id=target_id)
    )


def matches(conditions: list[dict[str, Any]], record: Any) -> bool:
    for condition in conditions:
        actual = getattr(record, condition["field"], None)
        value = condition["value"]
        if condition["operator"] == "equals" and str(actual).casefold() != value.casefold():
            return False
        if condition["operator"] == "contains" and value.casefold() not in str(actual).casefold():
            return False
        if condition["operator"] == "gte":
            try:
                if Decimal(str(actual)) < Decimal(value):
                    return False
            except (InvalidOperation, ValueError):
                return False
    return True


def on_crm_event(
    db: Session,
    user: User,
    entity_type: str,
    record: Any,
    action: str,
    changes: dict[str, Any] | None = None,
) -> None:
    """Runs in the caller's transaction. Actions do not recursively emit events."""
    del changes
    if db.info.get("automation_dispatch_depth", 0):
        return
    if record.org_id != user.org_id:
        raise ValueError("Automation tenant mismatch")
    aliases = {
        "create": "created",
        "update": "updated",
        "convert": "converted",
        "stage": "stage_changed",
        "complete": "completed",
    }
    event = f"{entity_type}.{aliases.get(action, action)}"
    rules = db.scalars(
        select(Automation).where(
            Automation.org_id == user.org_id,
            Automation.enabled.is_(True),
            Automation.trigger == event,
        )
    ).all()
    version = getattr(record, "version", 1)
    event_key = f"{event}:{record.id}:{version}"
    for rule in rules:
        if not matches(rule.conditions, record):
            continue
        existing = db.scalar(
            select(AutomationRun.id).where(
                AutomationRun.org_id == user.org_id,
                AutomationRun.rule_id == rule.id,
                AutomationRun.event_key == event_key,
            )
        )
        if existing:
            continue
        from app.modules.engagement.workflows import enqueue

        enqueue(db, rule, entity_type, record, event_key)


def update_automation(
    db: Session, user: User, record_id: str, values: dict[str, Any]
) -> dict[str, Any]:
    from app.core.db import ensure_write_transaction
    from app.modules.crm.service import serialize
    from app.modules.engagement.workflows import pause_pending, require_manager, validate_targets

    require_manager(user)
    ensure_write_transaction(db)
    row = db.scalar(
        select(Automation).where(Automation.org_id == user.org_id, Automation.id == record_id)
    )
    if row is None:
        raise HTTPException(404, "Automation not found.")
    validate_targets(db, user, values.get("steps", []))
    for key, value in values.items():
        setattr(row, key, value)
    if not row.enabled:
        pause_pending(db, row)
    db.commit()
    return serialize(row)
