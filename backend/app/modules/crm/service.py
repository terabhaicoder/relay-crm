import csv
import hashlib
import importlib
import io
import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, cast
from uuid import NAMESPACE_URL, uuid5

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import func, or_, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth import require_write
from app.core.db import ensure_write_transaction
from app.modules.auth.models import User
from app.modules.crm.models import (
    Activity,
    AuditEvent,
    Campaign,
    CampaignMember,
    Contact,
    Deal,
    IdempotencyRecord,
    Lead,
    Party,
    Pipeline,
    Stage,
    StageHistory,
    Ticket,
    TicketMessage,
    now,
)
from app.modules.crm.repository import CRMRepository
from app.modules.crm.schemas import SCHEMAS, ConvertLead, MessageInput


def serialize(record: Any) -> dict[str, Any]:
    result = {}
    for column in record.__table__.columns:
        if column.name in {"org_id", "deleted_at"}:
            continue
        value = getattr(record, column.name)
        if isinstance(value, Decimal):
            value = str(value.quantize(Decimal("0.01")))
        elif isinstance(value, datetime):
            value = (
                value.replace(tzinfo=UTC).isoformat() if value.tzinfo is None else value.isoformat()
            )
        result[column.name] = value
    return result


def record_event(
    db: Session,
    user: Any,
    entity_type: str,
    record: Any,
    action: str,
    changes: dict[str, Any] | None = None,
) -> None:
    db.add(
        AuditEvent(
            org_id=user.org_id,
            actor_id=user.id,
            entity_type=entity_type,
            entity_id=record.id,
            action=action,
            changes=changes or {},
        )
    )
    emit_automation(db, user, entity_type, record, action, changes)


def emit_automation(
    db: Session,
    user: Any,
    entity_type: str,
    record: Any,
    action: str,
    changes: dict[str, Any] | None = None,
) -> None:
    try:
        module = importlib.import_module("app.modules.engagement.service")
    except ModuleNotFoundError as error:
        if error.name not in {"app.modules.engagement", "app.modules.engagement.service"}:
            raise
    else:
        hook = getattr(module, "on_crm_event", None)
        if hook:
            hook(db, user, entity_type, record, action, changes or {})


def pipelines(db: Session, user: Any) -> list[dict[str, Any]]:
    rows = list(
        db.scalars(CRMRepository(db, user).query("pipelines").order_by(Pipeline.created_at))
    )
    if not rows:
        default_id = str(uuid5(NAMESPACE_URL, f"relay:{user.org_id}:default-pipeline"))
        try:
            with db.begin_nested():
                default = Pipeline(
                    id=default_id,
                    org_id=user.org_id,
                    owner_id=user.id,
                    name="Sales pipeline",
                )
                db.add(default)
                db.flush()
                specs = [
                    ("Discovery", 10, "open", "#8b94a5"),
                    ("Qualified", 30, "open", "#7696c8"),
                    ("Proposal", 60, "open", "#b38ae1"),
                    ("Negotiation", 80, "open", "#dea04e"),
                    ("Won", 100, "won", "#5a9c76"),
                    ("Lost", 0, "lost", "#cd7474"),
                ]
                for position, (name, probability, category, color) in enumerate(specs):
                    db.add(
                        Stage(
                            id=str(uuid5(NAMESPACE_URL, f"{default_id}:{position}")),
                            org_id=user.org_id,
                            pipeline_id=default.id,
                            name=name,
                            probability=probability,
                            position=position,
                            category=category,
                            color=color,
                        )
                    )
                db.flush()
        except IntegrityError:
            # Another request created the same deterministic default while we waited.
            existing = db.scalar(
                select(Pipeline).where(
                    Pipeline.org_id == user.org_id,
                    Pipeline.id == default_id,
                    Pipeline.deleted_at.is_(None),
                )
            )
            if existing is None:
                raise HTTPException(409, "Pipeline setup changed. Please refresh.") from None
        rows = list(
            db.scalars(CRMRepository(db, user).query("pipelines").order_by(Pipeline.created_at))
        )
    stage_rows = list(
        db.scalars(select(Stage).where(Stage.org_id == user.org_id).order_by(Stage.position))
    )
    return [
        {
            **serialize(row),
            "stages": [serialize(stage) for stage in stage_rows if stage.pipeline_id == row.id],
        }
        for row in rows
    ]


def validate_references(db: Session, user: Any, entity: str, data: dict[str, Any]) -> None:
    repo = CRMRepository(db, user)
    if (
        user.role in {"Sales Rep", "Sales Representative"}
        and "owner_id" in data
        and not data["owner_id"]
    ):
        raise HTTPException(403, "You can only assign your own records.")
    if data.get("owner_id"):
        owner = db.scalar(
            select(User).where(
                User.id == data["owner_id"], User.org_id == user.org_id, User.is_active.is_(True)
            )
        )
        if owner is None:
            raise HTTPException(404, "Owner not found.")
        if user.role in {"Sales Rep", "Sales Representative"} and owner.id != user.id:
            raise HTTPException(403, "You can only assign your own records.")
    for key, target in [("party_id", "parties"), ("contact_id", "contacts"), ("deal_id", "deals")]:
        if data.get(key):
            repo.get(target, data[key])
    if data.get("party_id") and data.get("contact_id"):
        contact = repo.get("contacts", data["contact_id"])
        if contact.party_id and contact.party_id != data["party_id"]:
            raise HTTPException(422, "The selected contact belongs to a different company.")
    if data.get("deal_id"):
        deal = repo.get("deals", data["deal_id"])
        if data.get("party_id") and deal.party_id and deal.party_id != data["party_id"]:
            raise HTTPException(422, "The selected deal belongs to a different company.")
        if data.get("contact_id") and deal.party_id:
            contact = repo.get("contacts", data["contact_id"])
            if contact.party_id and contact.party_id != deal.party_id:
                raise HTTPException(
                    422, "The selected contact and deal belong to different companies."
                )
    if data.get("entity_id"):
        related_type = data.get("entity_type")
        if related_type not in {"leads", "contacts", "parties", "deals", "tickets", "campaigns"}:
            raise HTTPException(422, "Choose a supported related record type.")
        repo.get(str(related_type), data["entity_id"])
    elif data.get("entity_type"):
        raise HTTPException(422, "Choose a related record.")
    for key in ("next_follow_up", "expected_close_date", "due_date", "start_date", "end_date"):
        if data.get(key):
            try:
                datetime.fromisoformat(data[key].replace("Z", "+00:00"))
            except (ValueError, TypeError):
                raise HTTPException(422, f"{key} must be a valid ISO date or datetime.") from None
    if data.get("start_date") and data.get("end_date") and data["end_date"] < data["start_date"]:
        raise HTTPException(422, "End date must be after start date.")


def validated(entity: str, data: dict[str, Any], partial: bool = False) -> dict[str, Any]:
    if entity not in SCHEMAS:
        raise HTTPException(404, "Collection not found.")
    try:
        parsed = SCHEMAS[entity].model_validate(data)
    except ValidationError as error:
        raise HTTPException(
            422,
            {
                "message": "Check the highlighted fields.",
                "fields": [
                    {"field": ".".join(str(p) for p in item["loc"]), "message": item["msg"]}
                    for item in error.errors()
                ],
            },
        ) from None
    values = parsed.model_dump(exclude_unset=partial)
    values.pop("version", None)
    if (not partial or "name" in values) and not values.get("name"):
        raise HTTPException(422, "Name is required.")
    return values


def create(db: Session, user: Any, entity: str, payload: dict[str, Any]) -> Any:
    require_write(user)
    values = validated(entity, payload)
    values["owner_id"] = values.get("owner_id") or user.id
    validate_references(db, user, entity, values)
    if entity == "leads" and values.get("status") == "Converted":
        raise HTTPException(422, "Use Convert lead to create linked records.")
    if entity == "deals":
        available = pipelines(db, user)
        if not values.get("stage_id"):
            pipeline_id = values.get("pipeline_id") or available[0]["id"]
            possible = next((p for p in available if p["id"] == pipeline_id), None)
            if not possible:
                raise HTTPException(404, "Pipeline not found.")
            values["stage_id"] = next(
                s["id"] for s in possible["stages"] if s["category"] == "open"
            )
        stage = CRMRepository(db, user).stage(values["stage_id"])
        if values.get("pipeline_id") and values["pipeline_id"] != stage.pipeline_id:
            raise HTTPException(422, "Stage must belong to the selected pipeline.")
        if values.get("status", "open") != "open":
            raise HTTPException(422, "Create an open deal, then close it with a reason.")
        if stage.category != "open":
            raise HTTPException(422, "Choose an open stage for a new deal.")
        values.update(
            pipeline_id=stage.pipeline_id, probability=stage.probability, status=stage.category
        )
    if entity == "activities" and values.get("status") == "completed":
        values["completed_at"] = now()
    if entity == "tickets" and values.get("status") in {"Resolved", "Closed"}:
        values["resolved_at"] = now()
    model = CRMRepository(db, user).model(entity)
    record = model(org_id=user.org_id, **values)
    db.add(record)
    db.flush()
    if entity == "deals":
        db.add(
            StageHistory(
                org_id=user.org_id, deal_id=record.id, to_stage_id=record.stage_id, actor_id=user.id
            )
        )
    record_event(db, user, entity, record, "created")
    return record


def modify(db: Session, user: Any, entity: str, record_id: str, payload: dict[str, Any]) -> Any:
    require_write(user)
    repo = CRMRepository(db, user)
    record = repo.get(entity, record_id, lock=True)
    values = validated(entity, payload, partial=True)
    if payload.get("version") and payload["version"] != record.version:
        raise HTTPException(409, "This record changed. Refresh and try again.")
    if entity == "leads" and (record.status == "Converted" or values.get("status") == "Converted"):
        raise HTTPException(
            409, "Converted leads are read-only. Edit their linked contact or deal."
        )
    if entity == "deals":
        for required_link in ("pipeline_id", "stage_id"):
            if required_link in values and not values[required_link]:
                raise HTTPException(422, "Deal pipeline and stage cannot be empty.")
        if record.status == "lost" and "lost_reason" in values and not values["lost_reason"]:
            raise HTTPException(422, "A lost deal must retain its reason.")
    if (
        entity == "activities"
        and record.entity_type == "activities"
        and values.get("entity_type", record.entity_type) == record.entity_type
        and values.get("entity_id", record.entity_id) == record.entity_id
    ):
        # Older automation runs linked their follow-up to the source activity.
        # Repair that unsupported relation only when this record is next edited,
        # and only through references the current user can still access.
        source = repo.get("activities", record.entity_id)
        visited = {record.id}
        while source.entity_type == "activities":
            if source.id in visited or len(visited) >= 100:
                raise HTTPException(
                    409, "This activity has a circular link. Choose a related record."
                )
            visited.add(source.id)
            source = repo.get("activities", source.entity_id)
        values.update(entity_type=source.entity_type, entity_id=source.entity_id)
    merged = {**serialize(record), **values}
    validate_references(db, user, entity, merged)
    if (
        entity in {"contacts", "deals"}
        and values.get("party_id")
        and values["party_id"] != record.party_id
    ):
        # Check all dependent records in this tenant, including those assigned to
        # colleagues. A master edit must not invalidate their existing links.
        dependents: list[tuple[Any, Any]] = (
            [(Deal, Deal.contact_id), (Ticket, Ticket.contact_id)]
            if entity == "contacts"
            else [(Ticket, Ticket.deal_id)]
        )
        for model, reference in dependents:
            conflict = db.scalar(
                select(model.id)
                .where(
                    model.org_id == user.org_id,
                    model.deleted_at.is_(None),
                    reference == record.id,
                    model.party_id.is_not(None),
                    model.party_id != values["party_id"],
                )
                .limit(1)
            )
            if conflict:
                raise HTTPException(
                    409,
                    "Linked records use another company. Unlink them before changing the company.",
                )
        opposite, ticket_link, edited_link = (
            (Deal, Ticket.deal_id, Ticket.contact_id)
            if entity == "contacts"
            else (Contact, Ticket.contact_id, Ticket.deal_id)
        )
        indirect_conflict = db.scalar(
            select(Ticket.id)
            .join(opposite, ticket_link == opposite.id)
            .where(
                Ticket.org_id == user.org_id,
                Ticket.deleted_at.is_(None),
                edited_link == record.id,
                opposite.org_id == user.org_id,
                opposite.deleted_at.is_(None),
                opposite.party_id.is_not(None),
                opposite.party_id != values["party_id"],
            )
            .limit(1)
        )
        if indirect_conflict:
            raise HTTPException(
                409,
                "Linked tickets use another company. Unlink them before changing the company.",
            )
    if entity == "deals":
        new_stage_id = values.get("stage_id")
        requested_status = values.get("status")
        if requested_status and requested_status != record.status and not new_stage_id:
            stage = db.scalar(
                select(Stage)
                .where(
                    Stage.org_id == user.org_id,
                    Stage.pipeline_id == record.pipeline_id,
                    Stage.category == requested_status,
                )
                .order_by(Stage.position)
            )
            if not stage:
                raise HTTPException(422, "Choose a valid stage.")
            new_stage_id = stage.id
        if new_stage_id and new_stage_id != record.stage_id:
            stage = repo.stage(new_stage_id)
            if stage.pipeline_id != record.pipeline_id:
                raise HTTPException(422, "Stage belongs to another pipeline.")
            reason = values.get("lost_reason") or record.lost_reason
            if stage.category == "lost" and not reason.strip():
                raise HTTPException(422, "A reason is required when a deal is lost.")
            values.update(
                stage_id=stage.id,
                status=stage.category,
                probability=stage.probability,
                stage_entered_at=now(),
                closed_at=now() if stage.category in {"won", "lost"} else None,
            )
            db.add(
                StageHistory(
                    org_id=user.org_id,
                    deal_id=record.id,
                    from_stage_id=record.stage_id,
                    to_stage_id=stage.id,
                    actor_id=user.id,
                    reason=reason,
                )
            )
        elif requested_status and requested_status != record.status:
            raise HTTPException(422, "Status must match the selected stage.")
        if values.get("pipeline_id") and values["pipeline_id"] != record.pipeline_id:
            raise HTTPException(422, "Create a new deal to use another pipeline.")
    if entity == "deals" and values.get("status", record.status) in {"won", "lost"}:
        values["probability"] = 100 if values.get("status", record.status) == "won" else 0
    if entity == "activities" and "status" in values:
        values["completed_at"] = (
            (record.completed_at or now()) if values["status"] == "completed" else None
        )
    if entity == "tickets" and "status" in values:
        values["resolved_at"] = (
            (record.resolved_at or now()) if values["status"] in {"Resolved", "Closed"} else None
        )
    before = serialize(record)
    changes = {
        key: {
            "old": before.get(key),
            "new": str(value) if isinstance(value, (Decimal, datetime)) else value,
        }
        for key, value in values.items()
        if before.get(key) != value
    }
    expected = record.version
    statement = (
        update(type(record))
        .where(
            type(record).id == record.id,
            type(record).org_id == user.org_id,
            type(record).version == expected,
        )
        .values(**values, version=expected + 1, updated_at=now())
    )
    if (
        cast(
            CursorResult[Any], db.execute(statement.execution_options(synchronize_session=False))
        ).rowcount
        != 1
    ):
        raise HTTPException(409, "This record changed. Refresh and try again.")
    db.expire(record)
    db.refresh(record)
    record_event(db, user, entity, record, "updated", changes)
    if entity == "deals" and before.get("stage_id") != record.stage_id:
        emit_automation(db, user, entity, record, "stage_changed", changes)
        if record.status in {"won", "lost"} and before.get("status") != record.status:
            emit_automation(db, user, entity, record, record.status, changes)
    if (
        entity == "activities"
        and record.status == "completed"
        and before.get("status") != "completed"
    ):
        emit_automation(db, user, entity, record, "completed", changes)
    return record


def convert_lead(db: Session, user: Any, lead_id: str, payload: ConvertLead) -> dict[str, Any]:
    require_write(user)
    repo = CRMRepository(db, user)
    lead = repo.get("leads", lead_id, lock=True)
    if lead.converted_contact_id:
        return {
            "contact": serialize(repo.get("contacts", lead.converted_contact_id)),
            "party": serialize(repo.get("parties", lead.converted_party_id))
            if lead.converted_party_id
            else None,
            "deal": serialize(repo.get("deals", lead.converted_deal_id))
            if lead.converted_deal_id
            else None,
            "already_converted": True,
        }
    expected = lead.version
    claimed = db.execute(
        update(Lead)
        .where(
            Lead.id == lead.id,
            Lead.org_id == user.org_id,
            Lead.version == expected,
            Lead.converted_contact_id.is_(None),
        )
        .values(version=expected + 1)
        .execution_options(synchronize_session=False)
    )
    if cast(CursorResult[Any], claimed).rowcount != 1:
        raise HTTPException(
            409, "This lead is being converted. Refresh to open its linked records."
        )
    existing_contact = repo.get("contacts", payload.contact_id) if payload.contact_id else None
    party_id = payload.party_id or (existing_contact.party_id if existing_contact else None)
    party = (
        repo.get("parties", party_id)
        if party_id
        else create(
            db,
            user,
            "parties",
            {
                "name": lead.company or lead.name,
                "email": lead.email,
                "phone": lead.phone,
                "owner_id": lead.owner_id,
            },
        )
    )
    if existing_contact and existing_contact.party_id and existing_contact.party_id != party.id:
        raise HTTPException(422, "The existing contact belongs to a different account.")
    if existing_contact:
        contact = existing_contact
        if not contact.party_id:
            contact = modify(
                db,
                user,
                "contacts",
                contact.id,
                {
                    "party_id": party.id,
                    "company": contact.company or party.name,
                    "version": contact.version,
                },
            )
    else:
        contact = create(
            db,
            user,
            "contacts",
            {
                "name": lead.name,
                "company": party.name,
                "party_id": party.id,
                "email": lead.email,
                "phone": lead.phone,
                "title": lead.title,
                "owner_id": lead.owner_id,
            },
        )
    deal = (
        create(
            db,
            user,
            "deals",
            {
                "name": payload.deal_name or f"{party.name} opportunity",
                "party_id": party.id,
                "contact_id": contact.id,
                "amount": payload.amount if payload.amount is not None else lead.value,
                "owner_id": lead.owner_id,
            },
        )
        if payload.create_deal
        else None
    )
    lead.status = "Converted"
    lead.converted_party_id, lead.converted_contact_id, lead.converted_deal_id = (
        party.id,
        contact.id,
        deal.id if deal else None,
    )
    lead.version = expected + 1
    record_event(
        db,
        user,
        "leads",
        lead,
        "converted",
        {"contact_id": contact.id, "party_id": party.id, "deal_id": deal.id if deal else None},
    )
    db.flush()
    return {
        "contact": serialize(contact),
        "party": serialize(party),
        "deal": serialize(deal) if deal else None,
        "already_converted": False,
    }


def idempotent_result(
    db: Session, user: Any, key: str | None, route: str, payload: dict[str, Any]
) -> tuple[dict[str, Any] | None, str]:
    hashed = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()
    if key:
        if len(key) > 200:
            raise HTTPException(422, "Idempotency key is too long.")
        previous = db.scalar(
            select(IdempotencyRecord).where(
                IdempotencyRecord.org_id == user.org_id,
                IdempotencyRecord.key == key,
                IdempotencyRecord.route == route,
            )
        )
        if previous:
            if previous.payload_hash != hashed:
                raise HTTPException(409, "This request key was already used with different data.")
            return previous.response, hashed
    return None, hashed


def remember(
    db: Session, user: Any, key: str | None, route: str, digest: str, response: dict[str, Any]
) -> None:
    if key:
        db.add(
            IdempotencyRecord(
                org_id=user.org_id, key=key, route=route, payload_hash=digest, response=response
            )
        )


def execute_idempotent(
    db: Session,
    user: Any,
    key: str | None,
    route: str,
    payload: dict[str, Any],
    create_response: Callable[[], dict[str, Any]],
    replay: Callable[[dict[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    """Commit a module-owned create and its retry marker in the same transaction."""
    previous, digest = idempotent_result(db, user, key, route, payload)
    if previous:
        return replay(previous)
    try:
        result = create_response()
        remember(db, user, key, route, digest, result)
        db.commit()
        return result
    except IntegrityError:
        db.rollback()
        previous, _ = idempotent_result(db, user, key, route, payload)
        if previous:
            return replay(previous)
        raise HTTPException(
            409, "This record conflicts with existing data. Refresh and retry."
        ) from None


def dashboard(db: Session, user: Any, period: str = "all") -> dict[str, Any]:
    repo = CRMRepository(db, user)
    days = {"all": None, "7d": 7, "30d": 30, "90d": 90}.get(period)
    if period not in {"all", "7d", "30d", "90d"}:
        raise HTTPException(422, "Choose all, 7d, 30d or 90d.")
    cutoff = now() - timedelta(days=days) if days else None

    def scoped_rows(model: Any) -> list[Any]:
        conditions: list[Any] = repo.scope(model)
        if cutoff:
            conditions.append(model.created_at >= cutoff)
        return conditions

    counts = {
        entity: db.scalar(select(func.count()).select_from(model).where(*scoped_rows(model))) or 0
        for entity, model in [
            ("leads", Lead),
            ("contacts", Contact),
            ("parties", Party),
            ("deals", Deal),
            ("activities", Activity),
            ("campaigns", Campaign),
            ("tickets", Ticket),
        ]
    }
    scoped = scoped_rows(Deal)
    pipeline_value = Decimal("0")
    weighted = Decimal("0")
    won_value = Decimal("0")
    status_counts: dict[str, int] = {}
    values: dict[str, tuple[int, Decimal]] = {}
    deal_rows = db.execute(
        select(Deal.stage_id, Deal.status, Deal.amount, Deal.probability).where(*scoped)
    ).yield_per(500)
    # Stream on the server: Decimal totals must not use SQLite's floating SUM/product.
    for stage_id, status, amount, probability in deal_rows:
        status_counts[status] = status_counts.get(status, 0) + 1
        count, stage_amount = values.get(stage_id, (0, Decimal("0")))
        values[stage_id] = (count + 1, stage_amount + amount)
        if status == "open":
            pipeline_value += amount
            weighted += amount * Decimal(probability) / Decimal("100")
        elif status == "won":
            won_value += amount
    won_count, lost_count = status_counts.get("won", 0), status_counts.get("lost", 0)
    today = now().date().isoformat()
    pending = scoped_rows(Activity) + [Activity.status == "pending"]
    overdue = (
        db.scalar(
            select(func.count()).select_from(Activity).where(*pending, Activity.due_date < today)
        )
        or 0
    )
    upcoming = list(
        db.scalars(
            select(Activity)
            .where(*pending)
            .order_by(Activity.due_date.is_(None), Activity.due_date)
            .limit(6)
        )
    )
    stage_data = []
    for pipe in pipelines(db, user):
        for stage in pipe["stages"]:
            count, amount = values.get(stage["id"], (0, 0))
            stage_data.append(
                {
                    **stage,
                    "count": count,
                    "value": str(Decimal(amount or 0).quantize(Decimal("0.01"))),
                }
            )
    sources = [
        {"source": source, "count": count}
        for source, count in db.execute(
            select(Lead.source, func.count()).where(*scoped_rows(Lead)).group_by(Lead.source)
        ).all()
    ]
    visible_events = []
    for entity, model in (
        ("leads", Lead),
        ("contacts", Contact),
        ("parties", Party),
        ("deals", Deal),
        ("activities", Activity),
        ("campaigns", Campaign),
        ("tickets", Ticket),
    ):
        visible_events.append(
            (AuditEvent.entity_type == entity)
            & AuditEvent.entity_id.in_(select(model.id).where(*repo.scope(model)))
        )
    recent = list(
        db.scalars(
            select(AuditEvent)
            .where(AuditEvent.org_id == user.org_id, or_(*visible_events))
            .order_by(AuditEvent.created_at.desc())
            .limit(8)
        )
    )
    open_tickets = (
        db.scalar(
            select(func.count())
            .select_from(Ticket)
            .where(*scoped_rows(Ticket), Ticket.status.not_in(["Resolved", "Closed"]))
        )
        or 0
    )
    return {
        "period": period,
        "period_basis": "records_created",
        "period_start": cutoff.isoformat() if cutoff else None,
        "counts": counts,
        "pipeline_value": str(Decimal(pipeline_value or 0).quantize(Decimal("0.01"))),
        "weighted_pipeline": str(Decimal(weighted or 0).quantize(Decimal("0.01"))),
        "won_value": str(Decimal(won_value or 0).quantize(Decimal("0.01"))),
        "open_deals": status_counts.get("open", 0),
        "won_deals": won_count,
        "lost_deals": lost_count,
        "win_rate": round(won_count / (won_count + lost_count) * 100, 1)
        if won_count + lost_count
        else 0,
        "overdue_tasks": overdue,
        "open_tickets": open_tickets,
        "stages": stage_data,
        "sources": sources,
        "upcoming_activities": [serialize(item) for item in upcoming],
        "recent_activity": [serialize(item) for item in recent],
    }


def export_csv(
    db: Session,
    user: Any,
    entity: str,
    *,
    q: str = "",
    status: str | None = None,
    owner_id: str | None = None,
    stage_id: str | None = None,
    pipeline_id: str | None = None,
    sort: str = "created_at",
    order: str = "asc",
) -> str:
    """Export every matching, permission-scoped row, independently of UI pagination."""
    if entity not in SCHEMAS:
        raise HTTPException(404, "Collection not found.")
    repo = CRMRepository(db, user)
    output = io.StringIO()
    fields = [key for key in SCHEMAS[entity].model_fields if key != "version"]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    offset = 0
    while True:
        records, total = repo.list(
            entity,
            q=q,
            status=status or None,
            owner_id=owner_id or None,
            stage_id=stage_id or None,
            pipeline_id=pipeline_id or None,
            limit=500,
            offset=offset,
            sort=sort,
            order=order,
        )
        for record in records:
            data = serialize(record)
            row = {}
            for key in fields:
                value = data.get(key, "")
                if isinstance(value, list):
                    # JSON preserves literal semicolons and Unicode within individual tags.
                    value = json.dumps(value, ensure_ascii=False)
                if isinstance(value, str) and value.startswith(
                    ("'", "=", "+", "-", "@", "\t", "\r", "\n")
                ):
                    value = "'" + value
                row[key] = value
            writer.writerow(row)
        offset += len(records)
        if not records or offset >= total:
            break
    return output.getvalue()


def import_csv(db: Session, user: Any, entity: str, content: str, mode: str) -> dict[str, Any]:
    require_write(user)
    if entity not in SCHEMAS:
        raise HTTPException(404, "Collection not found.")
    reader = csv.DictReader(io.StringIO(content.lstrip("\ufeff")), strict=True)
    try:
        headers = reader.fieldnames
    except csv.Error as error:
        raise HTTPException(422, f"Invalid CSV header: {error}.") from None
    if not headers or "name" not in headers:
        raise HTTPException(422, "CSV needs a name column. Export a file to see available columns.")
    if len(set(headers)) != len(headers):
        raise HTTPException(422, "CSV column names must be unique.")
    unknown = set(headers) - set(SCHEMAS[entity].model_fields)
    if unknown:
        raise HTTPException(422, f"Unknown CSV columns: {', '.join(sorted(unknown))}.")
    created = updated_count = skipped = 0
    errors = []
    repo = CRMRepository(db, user)
    model = repo.model(entity)
    staged_rows = []
    try:
        for row in reader:
            staged_rows.append(row)
            if len(staged_rows) > 10000:
                raise HTTPException(422, "Import at most 10,000 rows per file.")
    except csv.Error as error:
        raise HTTPException(422, f"Invalid CSV near line {reader.line_num}: {error}.") from None
    ensure_write_transaction(db)
    for line, row in enumerate(staged_rows, 2):
        try:
            with db.begin_nested():
                if None in row or any(value is None for value in row.values()):
                    raise HTTPException(
                        422, "Row must have the same number of values as the header."
                    )
                payload = {
                    key: value
                    for key, value in row.items()
                    if key in SCHEMAS[entity].model_fields
                    and key != "version"
                    and (key == "name" or value not in (None, ""))
                }
                for key, value in list(payload.items()):
                    if (
                        isinstance(value, str)
                        and len(value) > 1
                        and value[0] == "'"
                        and value[1] in "'=+-@\t\r\n"
                    ):
                        payload[key] = value[1:]
                if payload.get("tags"):
                    raw_tags = payload["tags"]
                    if raw_tags.startswith("["):
                        payload["tags"] = json.loads(raw_tags)
                    else:
                        payload["tags"] = [tag.strip() for tag in raw_tags.split(";")]
                normalized = validated(entity, payload, partial=True)
                existing = None
                if mode != "create":
                    # Contact details take precedence over names, but ambiguous updates
                    # must never silently choose one of multiple matching records.
                    matches: dict[str, Any] = {}
                    for key in ("email", "phone", "name"):
                        if key == "name" and matches:
                            break
                        if normalized.get(key) and hasattr(model, key):
                            for match in db.scalars(
                                repo.query(entity).where(getattr(model, key) == normalized[key])
                            ):
                                matches[match.id] = match
                    if mode == "update" and len(matches) > 1:
                        raise HTTPException(
                            422,
                            "Multiple existing records match this row. "
                            "Resolve duplicates before updating.",
                        )
                    existing = next(iter(matches.values()), None)
                if existing and mode == "skip":
                    skipped += 1
                    continue
                if existing:
                    modify(db, user, entity, existing.id, payload)
                else:
                    create(db, user, entity, payload)
                db.flush()
                if existing:
                    updated_count += 1
                else:
                    created += 1
        except (HTTPException, ValueError, IntegrityError) as error:
            errors.append(
                {
                    "row": line,
                    "name": row.get("name", ""),
                    "message": str(
                        error.detail
                        if isinstance(error, HTTPException)
                        else "Record conflicts with existing data."
                        if isinstance(error, IntegrityError)
                        else error
                    ),
                }
            )
    error_output = io.StringIO()
    writer = csv.DictWriter(error_output, fieldnames=["row", "name", "message"])
    writer.writeheader()
    for error_row in errors:
        safe_row = {}
        for key, value in error_row.items():
            safe_row[key] = (
                "'" + value
                if isinstance(value, str)
                and value.startswith(("'", "=", "+", "-", "@", "\t", "\r", "\n"))
                else value
            )
        writer.writerow(safe_row)
    return {
        "created": created,
        "updated": updated_count,
        "skipped": skipped,
        "failed": len(errors),
        "errors": errors,
        "error_csv": error_output.getvalue(),
    }


def merge_leads(
    db: Session,
    user: Any,
    source_id: str,
    target_id: str,
    source_version: int | None = None,
    target_version: int | None = None,
) -> dict[str, Any]:
    """Keep target, archive source and retarget activities in one transaction."""
    require_write(user)
    if source_id == target_id:
        raise HTTPException(422, "Choose a different lead to keep.")
    repo = CRMRepository(db, user)
    records = {
        record_id: repo.get("leads", record_id, lock=True, include_deleted=True)
        for record_id in sorted([source_id, target_id])
    }
    source, target = records[source_id], records[target_id]
    if target.deleted_at is not None:
        raise HTTPException(404, "Lead not found.")
    if source.deleted_at is not None:
        prior = db.scalar(
            select(AuditEvent).where(
                AuditEvent.org_id == user.org_id,
                AuditEvent.entity_type == "leads",
                AuditEvent.entity_id == source_id,
                AuditEvent.action == "merged_into",
            )
        )
        if prior and prior.changes.get("target_id") == target_id:
            return {"lead": serialize(target), "moved_activities": 0, "already_merged": True}
        raise HTTPException(409, "This lead was already archived or merged elsewhere.")
    if source.status == "Converted" or target.status == "Converted":
        raise HTTPException(409, "Converted leads cannot be merged. Use their linked records.")
    if source_version is not None and source_version != source.version:
        raise HTTPException(409, "The source lead changed. Refresh before merging.")
    if target_version is not None and target_version != target.version:
        raise HTTPException(409, "The lead you want to keep changed. Refresh before merging.")
    expected = source.version
    claimed = db.execute(
        update(Lead)
        .where(
            Lead.id == source_id,
            Lead.org_id == user.org_id,
            Lead.version == expected,
            Lead.deleted_at.is_(None),
        )
        .values(version=expected + 1)
        .execution_options(synchronize_session=False)
    )
    if cast(CursorResult[Any], claimed).rowcount != 1:
        raise HTTPException(409, "This lead changed while merging. Refresh and try again.")
    patch: dict[str, Any] = {"version": target.version}
    for field in ("email", "phone", "company", "title", "source", "next_follow_up"):
        if not getattr(target, field) and getattr(source, field):
            patch[field] = getattr(source, field)
    tags = list(dict.fromkeys([*(target.tags or []), *(source.tags or [])]))
    patch["tags"] = tags
    if source.notes and source.notes != target.notes:
        patch["notes"] = (target.notes + f"\n\nMerged from {source.name}:\n" + source.notes).strip()
    target = modify(db, user, "leads", target_id, patch)
    moved = db.execute(
        update(Activity)
        .where(
            Activity.org_id == user.org_id,
            Activity.entity_type == "leads",
            Activity.entity_id == source_id,
            Activity.deleted_at.is_(None),
        )
        .values(entity_id=target_id, updated_at=now(), version=Activity.version + 1)
    )
    moved_count = cast(CursorResult[Any], moved).rowcount
    for module_name, function_name in (
        ("app.modules.files.service", "relink_entity"),
        ("app.modules.engagement.service", "relink_entity"),
    ):
        try:
            owner_service = importlib.import_module(module_name)
        except ModuleNotFoundError as error:
            if error.name not in {module_name, module_name.rsplit(".", 1)[0]}:
                raise
        else:
            relink = getattr(owner_service, function_name, None)
            if relink:
                relink(db, user, "leads", source_id, target_id)
    existing_campaigns = set(
        db.scalars(
            select(CampaignMember.campaign_id).where(
                CampaignMember.org_id == user.org_id,
                CampaignMember.entity_type == "leads",
                CampaignMember.entity_id == target_id,
            )
        )
    )
    for membership in db.scalars(
        select(CampaignMember).where(
            CampaignMember.org_id == user.org_id,
            CampaignMember.entity_type == "leads",
            CampaignMember.entity_id == source_id,
        )
    ):
        if membership.campaign_id in existing_campaigns:
            db.delete(membership)
        else:
            membership.entity_id = target_id
    source.deleted_at = now()
    source.version = expected + 1
    source.updated_at = now()
    record_event(db, user, "leads", source, "merged_into", {"target_id": target_id})
    record_event(
        db,
        user,
        "leads",
        target,
        "merged",
        {
            "source_id": source_id,
            "source_name": source.name,
            "moved_activities": moved_count,
        },
    )
    db.flush()
    return {"lead": serialize(target), "moved_activities": moved_count, "already_merged": False}


def record_timeline(db: Session, user: Any, entity: str, record_id: str) -> dict[str, Any]:
    CRMRepository(db, user).get(entity, record_id)
    record_ids = {record_id}
    pending = [record_id]
    # Merged histories are retained in place and followed through immutable audit links.
    while pending and entity == "leads" and len(record_ids) < 100:
        current = pending.pop()
        merges = db.scalars(
            select(AuditEvent).where(
                AuditEvent.org_id == user.org_id,
                AuditEvent.entity_type == entity,
                AuditEvent.entity_id == current,
                AuditEvent.action == "merged",
            )
        )
        for merge in merges:
            source_id = merge.changes.get("source_id")
            if isinstance(source_id, str) and source_id not in record_ids:
                record_ids.add(source_id)
                pending.append(source_id)
    rows = db.scalars(
        select(AuditEvent)
        .where(
            AuditEvent.org_id == user.org_id,
            AuditEvent.entity_type == entity,
            AuditEvent.entity_id.in_(record_ids),
        )
        .order_by(AuditEvent.created_at.desc())
        .limit(100)
    )
    return {"items": [serialize(row) for row in rows]}


def archive_record(db: Session, user: Any, entity: str, record_id: str) -> None:
    """Do not leave active relationships pointing at an inaccessible archived master."""
    require_write(user)
    repo = CRMRepository(db, user)
    record = repo.get(entity, record_id, lock=True)
    if entity == "leads" and record.status == "Converted":
        raise HTTPException(409, "Keep converted leads for their linked history.")
    if entity == "pipelines":
        raise HTTPException(
            409, "Pipelines cannot be deleted while their stage history is retained."
        )
    expected = record.version
    claimed = db.execute(
        update(type(record))
        .where(
            type(record).org_id == user.org_id,
            type(record).id == record_id,
            type(record).version == expected,
            type(record).deleted_at.is_(None),
        )
        .values(version=expected + 1)
        .execution_options(synchronize_session=False)
    )
    if cast(CursorResult[Any], claimed).rowcount != 1:
        raise HTTPException(409, "This record changed. Refresh before deleting.")
    references: dict[str, list[tuple[Any, Any]]] = {
        "parties": [
            (Contact, Contact.party_id),
            (Deal, Deal.party_id),
            (Ticket, Ticket.party_id),
            (Lead, Lead.converted_party_id),
        ],
        "contacts": [
            (Deal, Deal.contact_id),
            (Ticket, Ticket.contact_id),
            (Lead, Lead.converted_contact_id),
        ],
        "deals": [(Ticket, Ticket.deal_id), (Lead, Lead.converted_deal_id)],
        "pipelines": [(Deal, Deal.pipeline_id)],
    }
    for model, foreign_key in references.get(entity, []):
        linked = db.scalar(
            select(model.id)
            .where(
                model.org_id == user.org_id,
                model.deleted_at.is_(None),
                foreign_key == record_id,
            )
            .limit(1)
        )
        if linked:
            raise HTTPException(409, "This record has linked records. Unlink them before deleting.")
    linked_activity = db.scalar(
        select(Activity.id)
        .where(
            Activity.org_id == user.org_id,
            Activity.deleted_at.is_(None),
            Activity.entity_type == entity,
            Activity.entity_id == record_id,
        )
        .limit(1)
    )
    if linked_activity:
        raise HTTPException(409, "This record has linked activities. Unlink them before deleting.")
    record.deleted_at = now()
    record.updated_at = now()
    record.version = expected + 1
    record_event(db, user, entity, record, "deleted")
    db.flush()


def post_ticket_message(
    db: Session,
    user: Any,
    ticket_id: str,
    payload: MessageInput,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    require_write(user)
    ticket = CRMRepository(db, user).get("tickets", ticket_id)
    route = f"{user.id}/tickets/{ticket_id}/messages"
    data = payload.model_dump()
    previous, digest = idempotent_result(db, user, idempotency_key, route, data)
    if previous:
        return previous
    try:
        message = TicketMessage(
            org_id=user.org_id,
            ticket_id=ticket_id,
            author_id=user.id,
            body=payload.body,
            internal=payload.internal,
        )
        db.add(message)
        db.flush()
        record_event(
            db, user, "tickets", ticket, "internal_note" if payload.internal else "reply_drafted"
        )
        result = {
            **serialize(message),
            "delivery_status": "internal" if payload.internal else "draft",
        }
        remember(db, user, idempotency_key, route, digest, result)
        db.commit()
    except IntegrityError:
        db.rollback()
        previous, _ = idempotent_result(db, user, idempotency_key, route, data)
        if previous:
            CRMRepository(db, user).get("tickets", ticket_id)
            return previous
        raise HTTPException(
            409, "The conversation changed. Please refresh and try again."
        ) from None
    return result
