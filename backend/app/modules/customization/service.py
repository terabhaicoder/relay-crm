import re
from datetime import date
from decimal import Decimal
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import require_write
from app.core.db import ensure_write_transaction
from app.modules.auth.models import User, utcnow
from app.modules.crm.service import execute_idempotent
from app.modules.customization.models import FieldAudit, FieldDefinition, RecordFields
from app.modules.customization.repository import CustomizationRepository
from app.modules.customization.schemas import (
    CustomDefinitionCreate,
    CustomDefinitionUpdate,
    CustomValuesUpdate,
    validate_options,
)

SUPPORTED_ENTITIES = {"leads", "contacts", "parties", "deals", "tickets"}


def require_manager(user: User) -> None:
    if user.role not in {"Owner", "Admin"}:
        raise HTTPException(403, "Only owners and administrators can manage custom fields.")


def encode(row: FieldDefinition) -> dict[str, Any]:
    return {
        "id": row.id,
        "entity": row.entity,
        "field_key": row.field_key,
        "label": row.label,
        "field_type": row.field_type,
        "description": row.description,
        "options": row.options,
        "archived": row.deleted_at is not None,
        "version": row.version,
    }


def audit(
    db: Session,
    user: User,
    entity: str,
    action: str,
    details: dict[str, Any],
    *,
    record_id: str | None = None,
    field_id: str | None = None,
) -> None:
    db.add(
        FieldAudit(
            org_id=user.org_id,
            entity=entity,
            record_id=record_id,
            field_id=field_id,
            actor_id=user.id,
            action=action,
            details=details,
        )
    )


def definitions(
    db: Session, user: User, entity: str, include_archived: bool, limit: int, offset: int
) -> dict[str, Any]:
    query = CustomizationRepository(db, user).definitions(entity, include_archived)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(FieldDefinition.created_at, FieldDefinition.id).offset(offset).limit(limit)
    )
    return {"items": [encode(row) for row in rows], "total": total}


def create_definition(
    db: Session, user: User, payload: CustomDefinitionCreate, key: str
) -> dict[str, Any]:
    require_manager(user)
    ensure_write_transaction(db)
    repo = CustomizationRepository(db, user)

    def create() -> dict[str, Any]:
        total = db.scalar(
            select(func.count()).select_from(repo.definitions(payload.entity, True).subquery())
        )
        if total is not None and total >= 100:
            raise HTTPException(409, "This collection has reached its 100-field limit.")
        row = FieldDefinition(
            org_id=user.org_id,
            created_by=user.id,
            updated_by=user.id,
            **payload.model_dump(),
        )
        db.add(row)
        db.flush()
        value = encode(row)
        audit(db, user, row.entity, "field_created", {"after": value}, field_id=row.id)
        db.flush()
        return value

    return execute_idempotent(
        db,
        user,
        key,
        f"{user.id}/custom-fields/definitions",
        payload.model_dump(),
        create,
        lambda previous: encode(repo.definition(previous["id"])),
    )


def update_definition(
    db: Session, user: User, field_id: str, payload: CustomDefinitionUpdate
) -> dict[str, Any]:
    require_manager(user)
    ensure_write_transaction(db)
    repo = CustomizationRepository(db, user)
    row = repo.definition(field_id)
    if row.version != payload.version:
        raise HTTPException(409, "This custom field changed. Reload before editing.")
    before = encode(row)
    if payload.options is not None:
        try:
            validate_options(row.field_type, payload.options)
        except ValueError as error:
            raise HTTPException(422, str(error)) from None
        removed = set(row.options) - set(payload.options)
        if removed:
            used = db.scalar(
                select(RecordFields.id)
                .where(
                    *repo.scope(RecordFields),
                    RecordFields.entity == row.entity,
                    RecordFields.values[row.id].as_string().in_(removed),
                )
                .limit(1)
            )
            if used:
                raise HTTPException(
                    409, "A removed choice is still in use. Keep it or update those records first."
                )
        row.options = payload.options
    if payload.label is not None:
        row.label = payload.label
    if payload.description is not None:
        row.description = payload.description
    if payload.archived is not None:
        row.deleted_at = utcnow() if payload.archived else None
    row.version += 1
    row.updated_at, row.updated_by = utcnow(), user.id
    after = encode(row)
    audit(
        db, user, row.entity, "field_updated", {"before": before, "after": after}, field_id=row.id
    )
    db.commit()
    return after


def record(db: Session, user: User, entity: str, record_id: str) -> dict[str, Any]:
    repo = CustomizationRepository(db, user)
    stored = repo.record_values(entity, record_id)
    values = stored.values if stored else {}
    rows = db.scalars(
        repo.definitions(entity, True).order_by(FieldDefinition.created_at, FieldDefinition.id)
    )
    fields = [
        encode(row) for row in rows if row.deleted_at is None or values.get(row.id) is not None
    ]
    events = db.scalars(
        select(FieldAudit)
        .where(
            *repo.scope(FieldAudit), FieldAudit.entity == entity, FieldAudit.record_id == record_id
        )
        .order_by(FieldAudit.created_at.desc(), FieldAudit.id)
        .limit(20)
    )
    return {
        "entity": entity,
        "record_id": record_id,
        "version": stored.version if stored else 0,
        "fields": fields,
        "values": values,
        "history": [
            {
                "action": event.action,
                "actor_id": event.actor_id,
                "created_at": event.created_at.isoformat()
                + ("+00:00" if event.created_at.tzinfo is None else ""),
                "changes": event.details.get("changes", []),
            }
            for event in events
        ],
    }


def validated_value(field: FieldDefinition, value: str | bool | None) -> str | bool | None:
    if value is None:
        return None
    if field.field_type == "boolean":
        if not isinstance(value, bool):
            raise HTTPException(422, f"{field.label}: choose Yes, No or Not set.")
        return value
    if not isinstance(value, str):
        raise HTTPException(422, f"{field.label}: provide a text value.")
    if field.field_type == "text":
        if len(value) > 2000:
            raise HTTPException(422, f"{field.label}: use at most 2,000 characters.")
        return value
    if field.field_type == "number":
        if not re.fullmatch(r"-?\d{1,12}(?:\.\d{1,6})?", value):
            raise HTTPException(
                422, f"{field.label}: use up to 12 integer and 6 decimal digits, without commas."
            )
        number = Decimal(value)
        canonical = format(number, "f")
        if "." in canonical:
            canonical = canonical.rstrip("0").rstrip(".")
        return "0" if number == 0 else canonical
    if field.field_type == "date":
        try:
            if date.fromisoformat(value).isoformat() != value:
                raise ValueError
        except ValueError:
            raise HTTPException(422, f"{field.label}: choose a valid YYYY-MM-DD date.") from None
        return value
    if value not in field.options:
        raise HTTPException(422, f"{field.label}: choose one of the configured options.")
    return value


def apply_values(
    db: Session,
    user: User,
    entity: str,
    record_id: str,
    payload: CustomValuesUpdate,
    *,
    action: str = "values_updated",
) -> None:
    repo = CustomizationRepository(db, user)
    parent = repo.get(entity, record_id)
    if entity == "leads" and parent.status == "Converted":
        raise HTTPException(409, "Converted leads are read-only. Edit their linked records.")
    stored = repo.record_values(entity, record_id)
    if payload.version != (stored.version if stored else 0):
        raise HTTPException(409, "These custom values changed. Reload before saving.")
    before = stored.values if stored else {}
    next_values = dict(before)
    changes = []
    # Validate the entire patch before writing any value or audit row.
    for field_id, value in payload.values.items():
        definition = repo.definition(field_id)
        if definition.entity != entity:
            raise HTTPException(422, "This custom field belongs to another collection.")
        if definition.deleted_at is not None:
            raise HTTPException(409, "Archived custom fields cannot be edited.")
        normalized = validated_value(definition, value)
        if before.get(field_id) != normalized:
            changes.append(
                {
                    "field_id": field_id,
                    "label": definition.label,
                    "before": before.get(field_id),
                    "after": normalized,
                }
            )
        next_values[field_id] = normalized
    if not changes:
        return
    if stored is None:
        stored = RecordFields(
            org_id=user.org_id,
            entity=entity,
            record_id=record_id,
            created_by=user.id,
            updated_by=user.id,
            values=next_values,
        )
        db.add(stored)
    else:
        stored.values = next_values
        stored.version += 1
        stored.updated_by, stored.updated_at = user.id, utcnow()
    audit(db, user, entity, action, {"changes": changes}, record_id=record_id)
    db.flush()


def save_record(
    db: Session,
    user: User,
    entity: str,
    record_id: str,
    payload: CustomValuesUpdate,
    key: str,
) -> dict[str, Any]:
    require_write(user)
    ensure_write_transaction(db)
    # Access is checked before replay as ownership may have changed.
    CustomizationRepository(db, user).get(entity, record_id)

    def save() -> dict[str, Any]:
        apply_values(db, user, entity, record_id, payload)
        return record(db, user, entity, record_id)

    return execute_idempotent(
        db,
        user,
        key,
        f"{user.id}/custom-fields/{entity}/{record_id}",
        payload.model_dump(),
        save,
        lambda _: record(db, user, entity, record_id),
    )


def copy_compatible_values(
    db: Session,
    user: User,
    source_entity: str,
    source_id: str,
    target_entity: str,
    target_id: str,
) -> int:
    """Optional caller-transaction hook; copy matching keys/types into empty values.

    No commit, no new definitions, no overwriting target data. The caller owns
    conversion/merge orchestration and calls before archiving the source record.
    """
    if source_entity not in SUPPORTED_ENTITIES or target_entity not in SUPPORTED_ENTITIES:
        return 0
    require_write(user)
    ensure_write_transaction(db)
    repo = CustomizationRepository(db, user)
    source = repo.record_values(source_entity, source_id)
    target = repo.record_values(target_entity, target_id)
    if source is None:
        return 0
    source_fields = {
        (row.field_key, row.field_type): row for row in db.scalars(repo.definitions(source_entity))
    }
    copied: dict[str, str | bool | None] = {}
    for target_field in db.scalars(repo.definitions(target_entity)):
        source_field = source_fields.get((target_field.field_key, target_field.field_type))
        if source_field is None or (target and target.values.get(target_field.id) is not None):
            continue
        value = source.values.get(source_field.id)
        if value is None or (
            target_field.field_type == "select" and value not in target_field.options
        ):
            continue
        copied[target_field.id] = value
    if copied:
        apply_values(
            db,
            user,
            target_entity,
            target_id,
            CustomValuesUpdate(version=target.version if target else 0, values=copied),
            action="values_copied",
        )
    return len(copied)
