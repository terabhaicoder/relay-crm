"""Scoped customer context, campaign membership and daily sales operations."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session

from app.core.auth import require_write
from app.core.db import ensure_write_transaction
from app.modules.crm.models import (
    Activity,
    AuditEvent,
    CampaignMember,
    Contact,
    Deal,
    Lead,
    Stage,
    StageHistory,
    Ticket,
    now,
)
from app.modules.crm.repository import CRMRepository, activity_day
from app.modules.crm.schemas import CampaignMemberInput, PipelineUpdate
from app.modules.crm.service import pipelines, record_event, serialize


def page(db: Session, query: Any, model: Any, limit: int, offset: int) -> dict[str, Any]:
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(query.order_by(model.updated_at.desc(), model.id).offset(offset).limit(limit))
    return {"items": [serialize(row) for row in rows], "total": total}


def overview(
    db: Session, user: Any, entity: str, record_id: str, limit: int, offset: int
) -> dict[str, Any]:
    if entity not in {"parties", "contacts"}:
        raise HTTPException(404, "Customer overview is available for companies and contacts.")
    repo = CRMRepository(db, user)
    record = repo.get(entity, record_id)
    contacts = (
        repo.query("contacts").where(Contact.party_id == record_id)
        if entity == "parties"
        else repo.query("contacts").where(Contact.id == record_id)
    )
    contact_ids = contacts.with_only_columns(Contact.id)
    deals = (
        repo.query("deals").where(or_(Deal.party_id == record_id, Deal.contact_id.in_(contact_ids)))
        if entity == "parties"
        else repo.query("deals").where(Deal.contact_id == record_id)
    )
    tickets = (
        repo.query("tickets").where(
            or_(
                Ticket.party_id == record_id,
                Ticket.contact_id.in_(contact_ids),
                Ticket.deal_id.in_(deals.with_only_columns(Deal.id)),
            )
        )
        if entity == "parties"
        else repo.query("tickets").where(
            or_(
                Ticket.contact_id == record_id, Ticket.deal_id.in_(deals.with_only_columns(Deal.id))
            )
        )
    )
    leads = (
        repo.query("leads").where(Lead.converted_party_id == record_id)
        if entity == "parties"
        else repo.query("leads").where(Lead.converted_contact_id == record_id)
    )
    queries = {"contacts": contacts, "deals": deals, "tickets": tickets, "leads": leads}
    links = [and_(Activity.entity_type == entity, Activity.entity_id == record_id)]
    audit_links = [and_(AuditEvent.entity_type == entity, AuditEvent.entity_id == record_id)]
    for name, query in queries.items():
        model = repo.model(name)
        ids = query.with_only_columns(model.id)
        links.append(and_(Activity.entity_type == name, Activity.entity_id.in_(ids)))
        audit_links.append(and_(AuditEvent.entity_type == name, AuditEvent.entity_id.in_(ids)))
    activities = repo.query("activities").where(or_(*links))
    queries["activities"] = activities
    audit_links.append(
        and_(
            AuditEvent.entity_type == "activities",
            AuditEvent.entity_id.in_(activities.with_only_columns(Activity.id)),
        )
    )
    timeline = select(AuditEvent).where(AuditEvent.org_id == user.org_id, or_(*audit_links))
    timeline_total = db.scalar(select(func.count()).select_from(timeline.subquery())) or 0
    timeline_rows = db.scalars(
        timeline.order_by(AuditEvent.created_at.desc(), AuditEvent.id).offset(offset).limit(limit)
    )
    amounts = list(db.execute(deals.with_only_columns(Deal.status, Deal.amount)))
    summary = {
        "open_deals": sum(status == "open" for status, _ in amounts),
        "won_deals": sum(status == "won" for status, _ in amounts),
        "open_pipeline": str(
            sum((amount for status, amount in amounts if status == "open"), Decimal("0.00"))
        ),
        "won_revenue": str(
            sum((amount for status, amount in amounts if status == "won"), Decimal("0.00"))
        ),
        "open_tickets": db.scalar(
            select(func.count()).select_from(
                tickets.where(Ticket.status.not_in(["Resolved", "Closed"])).subquery()
            )
        )
        or 0,
    }
    return {
        "record": serialize(record),
        "sections": {
            name: page(db, query, repo.model(name), limit, offset)
            for name, query in queries.items()
        },
        "summary": summary,
        "timeline": {"items": [serialize(row) for row in timeline_rows], "total": timeline_total},
    }


def member_query(repo: CRMRepository, campaign_id: str) -> Any:
    visible = []
    for entity in ("leads", "contacts"):
        model = repo.model(entity)
        visible.append(
            and_(
                CampaignMember.entity_type == entity,
                CampaignMember.entity_id.in_(repo.query(entity).with_only_columns(model.id)),
            )
        )
    return select(CampaignMember).where(
        CampaignMember.org_id == repo.user.org_id,
        CampaignMember.campaign_id == campaign_id,
        or_(*visible),
    )


def members(db: Session, user: Any, campaign_id: str, limit: int, offset: int) -> dict[str, Any]:
    repo = CRMRepository(db, user)
    repo.get("campaigns", campaign_id)
    query = member_query(repo, campaign_id)
    counts = {
        key: count
        for key, count in db.execute(
            select(CampaignMember.entity_type, func.count())
            .where(CampaignMember.id.in_(query.with_only_columns(CampaignMember.id)))
            .group_by(CampaignMember.entity_type)
        ).all()
    }
    lead_ids = query.where(CampaignMember.entity_type == "leads").with_only_columns(
        CampaignMember.entity_id
    )
    converted = (
        db.scalar(
            select(func.count()).select_from(
                repo.query("leads")
                .where(Lead.id.in_(lead_ids), Lead.status == "Converted")
                .subquery()
            )
        )
        or 0
    )
    rows = list(
        db.scalars(
            query.order_by(CampaignMember.created_at.desc(), CampaignMember.id)
            .offset(offset)
            .limit(limit)
        )
    )
    records: dict[str, Any] = {}
    for entity in ("leads", "contacts"):
        model = repo.model(entity)
        ids = [row.entity_id for row in rows if row.entity_type == entity]
        records.update(
            {
                f"{entity}:{row.id}": serialize(row)
                for row in db.scalars(repo.query(entity).where(model.id.in_(ids)))
            }
        )
    total = sum(counts.values())
    return {
        "items": [
            {**serialize(row), "record": records[f"{row.entity_type}:{row.entity_id}"]}
            for row in rows
        ],
        "total": total,
        "summary": {
            "members": total,
            "leads": counts.get("leads", 0),
            "contacts": counts.get("contacts", 0),
            "converted_leads": converted,
            "conversion_rate": round(converted * 100 / counts["leads"], 2)
            if counts.get("leads")
            else 0,
        },
    }


def add_member(
    db: Session, user: Any, campaign_id: str, payload: CampaignMemberInput
) -> dict[str, Any]:
    require_write(user)
    ensure_write_transaction(db)
    repo = CRMRepository(db, user)
    campaign = repo.get("campaigns", campaign_id, lock=True)
    record = repo.get(payload.entity_type, payload.entity_id)
    existing = db.scalar(
        member_query(repo, campaign_id).where(
            CampaignMember.entity_type == payload.entity_type,
            CampaignMember.entity_id == payload.entity_id,
        )
    )
    if existing:
        return {**serialize(existing), "record": serialize(record), "already_member": True}
    member = CampaignMember(
        org_id=user.org_id,
        campaign_id=campaign_id,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        created_by=user.id,
    )
    db.add(member)
    db.flush()
    record_event(
        db,
        user,
        "campaigns",
        campaign,
        "member_added",
        {"entity_type": payload.entity_type, "entity_id": payload.entity_id},
    )
    return {**serialize(member), "record": serialize(record), "already_member": False}


def remove_member(db: Session, user: Any, campaign_id: str, membership_id: str) -> None:
    require_write(user)
    ensure_write_transaction(db)
    repo = CRMRepository(db, user)
    campaign = repo.get("campaigns", campaign_id)
    member = db.scalar(member_query(repo, campaign_id).where(CampaignMember.id == membership_id))
    if member is None:
        raise HTTPException(404, "Campaign member not found.")
    record_event(
        db,
        user,
        "campaigns",
        campaign,
        "member_removed",
        {"entity_type": member.entity_type, "entity_id": member.entity_id},
    )
    db.delete(member)


def calendar(
    db: Session, user: Any, start: date, end: date, *, q: str = "", status: str | None = None
) -> dict[str, Any]:
    if end < start or (end - start).days > 61:
        raise HTTPException(422, "Choose a calendar range of at most 62 days.")
    repo = CRMRepository(db, user)
    day = activity_day()
    query = repo.query("activities").where(day >= start.isoformat(), day <= end.isoformat())
    if q:
        escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(Activity.name.ilike(f"%{escaped}%", escape="\\"))
    if status:
        query = query.where(Activity.status == status)
    counts = {
        key: count
        for key, count in db.execute(query.with_only_columns(day, func.count()).group_by(day)).all()
    }
    # A bounded range and three previews per day keep large calendars responsive.
    ranked = query.with_only_columns(
        Activity.id,
        day.label("day"),
        func.row_number()
        .over(partition_by=day, order_by=(Activity.due_date, Activity.id))
        .label("position"),
    ).subquery()
    rows = db.execute(
        select(Activity, ranked.c.day)
        .join(ranked, Activity.id == ranked.c.id)
        .where(ranked.c.position <= 3)
        .order_by(ranked.c.day, ranked.c.position)
    )
    previews: dict[str, list[dict[str, Any]]] = {}
    for record, key in rows:
        previews.setdefault(key, []).append(serialize(record))
    days = []
    for index in range((end - start).days + 1):
        key = (start + timedelta(days=index)).isoformat()
        days.append({"date": key, "count": counts.get(key, 0), "items": previews.get(key, [])})
    return {"days": days, "total": sum(counts.values())}


def board_summary(db: Session, user: Any, pipeline_id: str, q: str) -> dict[str, Any]:
    repo = CRMRepository(db, user)
    repo.get("pipelines", pipeline_id)
    query = repo.query("deals").where(Deal.pipeline_id == pipeline_id)
    if q:
        escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(Deal.name.ilike(f"%{escaped}%", escape="\\"))
    summary: dict[str, dict[str, Any]] = {}
    for stage in db.scalars(
        select(Stage)
        .where(Stage.org_id == user.org_id, Stage.pipeline_id == pipeline_id)
        .order_by(Stage.position)
    ):
        summary[stage.id] = {"id": stage.id, "total": 0, "amount": Decimal("0.00")}
    for stage_id, amount in db.execute(query.with_only_columns(Deal.stage_id, Deal.amount)):
        if stage_id in summary:
            summary[stage_id]["total"] += 1
            summary[stage_id]["amount"] += amount
    return {"stages": [{**value, "amount": str(value["amount"])} for value in summary.values()]}


def workbench(
    db: Session, user: Any, queue: str, limit: int, offset: int, owner_id: str | None
) -> dict[str, Any]:
    repo = CRMRepository(db, user)
    today = datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat()
    day = activity_day()
    activities = repo.query("activities").where(Activity.status == "pending")
    leads = repo.query("leads").where(Lead.status.not_in(["Converted", "Unqualified"]))
    deals = repo.query("deals").where(Deal.status == "open")
    tickets = repo.query("tickets").where(Ticket.status.not_in(["Resolved", "Closed"]))
    if owner_id:
        activities = activities.where(Activity.owner_id == owner_id)
        leads = leads.where(Lead.owner_id == owner_id)
        deals = deals.where(Deal.owner_id == owner_id)
        tickets = tickets.where(Ticket.owner_id == owner_id)
    queues = {
        "overdue": ("activities", activities.where(day < today)),
        "today": ("activities", activities.where(day == today)),
        "upcoming": ("activities", activities.where(day > today)),
        "follow_up_leads": (
            "leads",
            leads.where(
                or_(
                    Lead.next_follow_up.is_(None),
                    case(
                        (func.length(Lead.next_follow_up) == 10, Lead.next_follow_up),
                        else_=func.date(Lead.next_follow_up, "+5 hours", "+30 minutes"),
                    )
                    <= today,
                )
            ),
        ),
        "stale_deals": (
            "deals",
            deals.where(Deal.stage_entered_at < datetime.now(UTC) - timedelta(days=14)),
        ),
        "open_tickets": ("tickets", tickets),
        "unassigned_tickets": (
            "tickets",
            repo.query("tickets").where(
                Ticket.status.not_in(["Resolved", "Closed"]), Ticket.owner_id.is_(None)
            ),
        ),
    }
    if queue not in queues:
        raise HTTPException(422, "Choose a supported work queue.")
    counts = {
        name: db.scalar(select(func.count()).select_from(query.subquery())) or 0
        for name, (_, query) in queues.items()
    }
    entity, query = queues[queue]
    if entity == "activities":
        query = query.order_by(Activity.due_date.asc(), Activity.id)
    elif entity == "leads":
        query = query.order_by(Lead.next_follow_up.asc(), Lead.id)
    elif entity == "deals":
        query = query.order_by(Deal.stage_entered_at.asc(), Deal.id)
    result = page(db, query, repo.model(entity), limit, offset)
    result["items"] = [{**row, "entity_type": entity} for row in result["items"]]
    return {**result, "counts": counts}


def update_pipeline(
    db: Session, user: Any, pipeline_id: str, payload: PipelineUpdate
) -> dict[str, Any]:
    require_write(user)
    ensure_write_transaction(db)
    if user.role not in {"Owner", "Admin", "Sales Manager"}:
        raise HTTPException(403, "Only workspace or sales managers can configure pipelines.")
    repo = CRMRepository(db, user)
    pipeline = repo.get("pipelines", pipeline_id, lock=True)
    if payload.stages is not None:
        stages = payload.stages
        if (
            sum(s.category == "won" for s in stages) != 1
            or sum(s.category == "lost" for s in stages) != 1
            or not any(s.category == "open" for s in stages)
        ):
            raise HTTPException(
                422, "Keep at least one open stage and exactly one won and lost stage."
            )
        if len({s.name.casefold() for s in stages}) != len(stages):
            raise HTTPException(422, "Stage names must be unique.")
        ids = [s.id for s in stages if s.id]
        if len(set(ids)) != len(ids):
            raise HTTPException(422, "Each stage can appear only once.")
        current = {
            s.id: s
            for s in db.scalars(
                select(Stage).where(Stage.org_id == user.org_id, Stage.pipeline_id == pipeline_id)
            )
        }
        for item in stages:
            if item.id and item.id not in current:
                raise HTTPException(404, "Stage not found in this pipeline.")
            if item.id and current[item.id].category != item.category:
                raise HTTPException(422, "An existing stage's outcome cannot change.")
            if (item.category == "won" and item.probability != 100) or (
                item.category == "lost" and item.probability != 0
            ):
                raise HTTPException(
                    422, "Won probability must be 100 and lost probability must be 0."
                )
        for stage_id, stage in current.items():
            if stage_id not in ids:
                used = db.scalar(
                    select(Deal.id)
                    .where(Deal.org_id == user.org_id, Deal.stage_id == stage_id)
                    .limit(1)
                )
                history = db.scalar(
                    select(StageHistory.id)
                    .where(
                        StageHistory.org_id == user.org_id,
                        or_(
                            StageHistory.from_stage_id == stage_id,
                            StageHistory.to_stage_id == stage_id,
                        ),
                    )
                    .limit(1)
                )
                if used or history:
                    raise HTTPException(
                        409, "A stage used by deals or their history cannot be removed."
                    )
                db.delete(stage)
        for position, item in enumerate(stages):
            updated_stage = current.get(item.id or "")
            previous_stage_probability = (
                updated_stage.probability if updated_stage is not None else None
            )
            if updated_stage is None:
                updated_stage = Stage(org_id=user.org_id, pipeline_id=pipeline_id)
                db.add(updated_stage)
            (
                updated_stage.name,
                updated_stage.probability,
                updated_stage.category,
                updated_stage.position,
            ) = (
                item.name,
                item.probability,
                item.category,
                position,
            )
            if (
                item.id
                and item.category == "open"
                and item.probability != previous_stage_probability
            ):
                affected_deals = db.scalars(
                    select(Deal).where(
                        Deal.org_id == user.org_id,
                        Deal.stage_id == item.id,
                        Deal.status == "open",
                        Deal.deleted_at.is_(None),
                        Deal.probability != item.probability,
                    )
                )
                for deal in affected_deals:
                    previous_probability = deal.probability
                    deal.probability = item.probability
                    deal.version += 1
                    deal.updated_at = now()
                    record_event(
                        db,
                        user,
                        "deals",
                        deal,
                        "updated",
                        {"probability": {"old": previous_probability, "new": item.probability}},
                    )
    if payload.name is not None:
        pipeline.name = payload.name
    pipeline.version += 1
    record_event(db, user, "pipelines", pipeline, "updated", payload.model_dump(exclude_unset=True))
    db.flush()
    return next(item for item in pipelines(db, user) if item["id"] == pipeline_id)
