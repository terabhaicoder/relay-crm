from datetime import timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from app.modules.auth.models import User, utcnow
from app.modules.engagement.models import (
    Automation,
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
) -> dict[str, Any]:
    model: Any = Automation if entity == "automations" else EmailDraft
    query = select(model).where(model.org_id == user.org_id)
    if model is EmailDraft and user.role in {"Sales Rep", "Sales Representative"}:
        query = query.where(model.owner_id == user.id)
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
    for model in (EmailDraft, Notification):
        db.execute(
            update(model)
            .where(
                model.org_id == user.org_id,
                model.entity_type == entity_type,
                model.entity_id == source_id,
            )
            .values(entity_id=target_id)
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
        title = rule.action_text.replace("{{name}}", record.name)
        recipient_id = getattr(record, "owner_id", None) or user.id
        result = "Notification created"
        if rule.action == "create_task":
            from app.modules.crm.models import Activity

            # Activity follow-ups keep the same customer context. Linking to an
            # activity itself produces an unsupported, uneditable CRM relation.
            linked_type = record.entity_type if entity_type == "activities" else entity_type
            linked_id = record.entity_id if entity_type == "activities" else record.id
            db.add(
                Activity(
                    org_id=user.org_id,
                    owner_id=recipient_id,
                    name=title,
                    type="task",
                    status="pending",
                    priority="medium",
                    due_date=(utcnow() + timedelta(days=rule.due_days)).date().isoformat(),
                    entity_type=linked_type,
                    entity_id=linked_id,
                    notes=f"Created by automation: {rule.name}",
                )
            )
            result = "Follow-up task created"
        db.add(
            Notification(
                org_id=user.org_id,
                user_id=recipient_id,
                title=title,
                entity_type=entity_type,
                entity_id=record.id,
            )
        )
        db.add(
            AutomationRun(
                org_id=user.org_id,
                rule_id=rule.id,
                event_key=event_key,
                entity_type=entity_type,
                entity_id=record.id,
                result=result,
            )
        )
        db.flush()
