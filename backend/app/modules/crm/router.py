from datetime import date
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Body, Header, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.auth import CurrentUser, SessionDep, require_write
from app.modules.crm import service, workspace
from app.modules.crm.models import (
    Pipeline,
    Stage,
    StageHistory,
    TicketMessage,
)
from app.modules.crm.repository import CRMRepository
from app.modules.crm.schemas import (
    CampaignMemberInput,
    ConvertLead,
    CSVImport,
    LeadMergeInput,
    LeadMergePair,
    MessageInput,
    PipelineInput,
    PipelineUpdate,
    StageChange,
)

router = APIRouter(tags=["CRM"])


@router.get("/dashboard")
@router.get("/dashboard/{role}")
def dashboard(
    db: SessionDep,
    user: CurrentUser,
    role: str = "owner",
    period: Literal["all", "7d", "30d", "90d"] = "all",
) -> dict[str, Any]:
    result = service.dashboard(db, user, period)
    db.commit()
    return result


@router.get("/reports/{name}")
def report(name: str, db: SessionDep, user: CurrentUser) -> dict[str, Any]:
    if name not in {
        "sales",
        "crm",
        "pipeline",
        "funnel",
        "sources",
        "win-loss",
        "support",
        "overview",
    }:
        raise HTTPException(404, "Report not found.")
    result = service.dashboard(db, user)
    db.commit()
    return result


@router.get("/pipelines")
def list_pipelines(db: SessionDep, user: CurrentUser) -> dict[str, Any]:
    result = service.pipelines(db, user)
    db.commit()
    return {"items": result}


@router.post("/pipelines", status_code=201)
def create_pipeline(
    payload: PipelineInput,
    db: SessionDep,
    user: CurrentUser,
    idempotency_key: str | None = Header(default=None),
) -> dict[str, Any]:
    require_write(user)

    def replay(previous: dict[str, Any]) -> dict[str, Any]:
        CRMRepository(db, user).get("pipelines", previous["id"])
        return next(p for p in service.pipelines(db, user) if p["id"] == previous["id"])

    def create_response() -> dict[str, Any]:
        pipeline = Pipeline(org_id=user.org_id, owner_id=user.id, name=payload.name)
        db.add(pipeline)
        db.flush()
        count = len(payload.stages)
        for index, name in enumerate([*payload.stages, "Won", "Lost"]):
            if not name.strip():
                raise HTTPException(422, "Stage name is required.")
            category = "won" if index == count else "lost" if index == count + 1 else "open"
            probability = (
                100
                if category == "won"
                else 0
                if category == "lost"
                else round((index + 1) / (count + 1) * 100)
            )
            db.add(
                Stage(
                    org_id=user.org_id,
                    pipeline_id=pipeline.id,
                    name=name,
                    probability=probability,
                    position=index,
                    category=category,
                )
            )
        db.flush()
        result = next(p for p in service.pipelines(db, user) if p["id"] == pipeline.id)
        return result

    return service.execute_idempotent(
        db,
        user,
        idempotency_key,
        f"{user.id}/pipelines",
        payload.model_dump(),
        create_response,
        replay,
    )


@router.get("/calendar")
def calendar_summary(
    db: SessionDep,
    user: CurrentUser,
    from_date: date,
    to_date: date,
    q: str = Query(default="", max_length=200),
    status: str | None = None,
) -> dict[str, Any]:
    return workspace.calendar(db, user, from_date, to_date, q=q, status=status)


@router.get("/deals/board-summary")
def board_summary(
    db: SessionDep, user: CurrentUser, pipeline_id: str, q: str = Query(default="", max_length=200)
) -> dict[str, Any]:
    return workspace.board_summary(db, user, pipeline_id, q)


@router.get("/workbench")
def workbench(
    db: SessionDep,
    user: CurrentUser,
    queue: str = "overdue",
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    owner_id: str | None = None,
) -> dict[str, Any]:
    return workspace.workbench(db, user, queue, limit, offset, owner_id)


@router.patch("/pipelines/{pipeline_id}")
def update_pipeline(
    pipeline_id: str, payload: PipelineUpdate, db: SessionDep, user: CurrentUser
) -> dict[str, Any]:
    result = workspace.update_pipeline(db, user, pipeline_id, payload)
    db.commit()
    return result


@router.get("/{entity}/{record_id}/overview")
def customer_overview(
    entity: str,
    record_id: str,
    db: SessionDep,
    user: CurrentUser,
    limit: int = Query(default=10, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    return workspace.overview(db, user, entity, record_id, limit, offset)


@router.get("/campaigns/{campaign_id}/members")
def campaign_members(
    campaign_id: str,
    db: SessionDep,
    user: CurrentUser,
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    return workspace.members(db, user, campaign_id, limit, offset)


@router.post("/campaigns/{campaign_id}/members", status_code=201)
def add_campaign_member(
    campaign_id: str, payload: CampaignMemberInput, db: SessionDep, user: CurrentUser
) -> dict[str, Any]:
    result = workspace.add_member(db, user, campaign_id, payload)
    db.commit()
    return result


@router.delete("/campaigns/{campaign_id}/members/{membership_id}", status_code=204)
def remove_campaign_member(
    campaign_id: str, membership_id: str, db: SessionDep, user: CurrentUser
) -> Response:
    workspace.remove_member(db, user, campaign_id, membership_id)
    db.commit()
    return Response(status_code=204)


@router.get("/search")
def search(
    db: SessionDep, user: CurrentUser, q: str = Query(min_length=1, max_length=200)
) -> dict[str, Any]:
    items = []
    repo = CRMRepository(db, user)
    for entity in ["leads", "contacts", "parties", "deals", "activities", "tickets"]:
        rows, _ = repo.list(entity, q=q, limit=5)
        for record in rows:
            items.append(
                {
                    "id": record.id,
                    "name": record.name,
                    "entity_type": entity,
                    "description": getattr(record, "company", "") or getattr(record, "status", ""),
                }
            )
    return {"items": items}


@router.get("/me/tasks")
def my_tasks(db: SessionDep, user: CurrentUser) -> dict[str, Any]:
    rows, total = CRMRepository(db, user).list(
        "activities", owner_id=user.id, sort="due_date", order="asc"
    )
    return {"items": [service.serialize(row) for row in rows], "total": total}


@router.get("/leads/duplicates")
def duplicate_leads(
    db: SessionDep, user: CurrentUser, phone: str = "", email: str = ""
) -> dict[str, Any]:
    from pydantic import ValidationError
    from sqlalchemy import or_

    from app.modules.crm.models import Lead
    from app.modules.crm.schemas import PersonInput

    try:
        parsed = PersonInput(phone=phone, email=email)
    except ValidationError:
        return {"items": [], "validation_pending": True}
    terms = []
    if parsed.phone:
        terms.append(Lead.phone == parsed.phone)
    if parsed.email:
        terms.append(Lead.email == parsed.email)
    if not terms:
        return {"items": []}
    rows = db.scalars(CRMRepository(db, user).query("leads").where(or_(*terms)).limit(20))
    return {"items": [service.serialize(row) for row in rows]}


@router.post("/leads/{record_id}/merge")
def merge_lead(
    record_id: str, payload: LeadMergeInput, db: SessionDep, user: CurrentUser
) -> dict[str, Any]:
    result = service.merge_leads(db, user, record_id, **payload.model_dump())
    db.commit()
    return result


@router.post("/leads/merge")
def merge_lead_pair(payload: LeadMergePair, db: SessionDep, user: CurrentUser) -> dict[str, Any]:
    result = service.merge_leads(db, user, **payload.model_dump())
    db.commit()
    return result


@router.post("/leads/{record_id}/convert")
def convert_lead(
    record_id: str,
    payload: ConvertLead,
    db: SessionDep,
    user: CurrentUser,
    idempotency_key: str | None = Header(default=None),
) -> dict[str, Any]:
    require_write(user)
    CRMRepository(db, user).get("leads", record_id)
    route = f"{user.id}/leads/{record_id}/convert"
    previous, digest = service.idempotent_result(
        db, user, idempotency_key, route, payload.model_dump()
    )
    if previous:
        repository = CRMRepository(db, user)
        for response_key, entity in (
            ("contact", "contacts"),
            ("party", "parties"),
            ("deal", "deals"),
        ):
            linked = previous.get(response_key)
            if isinstance(linked, dict) and linked.get("id"):
                repository.get(entity, linked["id"])
        return previous
    result = service.convert_lead(db, user, record_id, payload)
    service.remember(db, user, idempotency_key, route, digest, result)
    db.commit()
    return result


@router.patch("/deals/{record_id}/stage")
def change_stage(
    record_id: str, payload: StageChange, db: SessionDep, user: CurrentUser
) -> dict[str, Any]:
    values: dict[str, Any] = {"stage_id": payload.stage_id}
    if payload.version:
        values["version"] = payload.version
    if payload.reason:
        values["lost_reason"] = payload.reason
    record = service.modify(db, user, "deals", record_id, values)
    db.commit()
    return service.serialize(record)


@router.post("/deals/{record_id}/won")
def won(record_id: str, db: SessionDep, user: CurrentUser) -> dict[str, Any]:
    record = service.modify(db, user, "deals", record_id, {"status": "won"})
    db.commit()
    return service.serialize(record)


@router.post("/deals/{record_id}/lost")
def lost(
    record_id: str,
    db: SessionDep,
    user: CurrentUser,
    payload: Annotated[dict[str, Any], Body()],
) -> dict[str, Any]:
    reason = payload.get("reason") or payload.get("lost_reason") or ""
    if not isinstance(reason, str) or not reason.strip():
        raise HTTPException(422, "A reason is required when a deal is lost.")
    record = service.modify(db, user, "deals", record_id, {"status": "lost", "lost_reason": reason})
    db.commit()
    return service.serialize(record)


@router.get("/deals/{record_id}/history")
def deal_history(record_id: str, db: SessionDep, user: CurrentUser) -> dict[str, Any]:
    CRMRepository(db, user).get("deals", record_id)
    records = db.scalars(
        select(StageHistory)
        .where(StageHistory.org_id == user.org_id, StageHistory.deal_id == record_id)
        .order_by(StageHistory.created_at)
    )
    return {"items": [service.serialize(record) for record in records]}


@router.get("/tickets/{record_id}/messages")
def ticket_messages(record_id: str, db: SessionDep, user: CurrentUser) -> dict[str, Any]:
    CRMRepository(db, user).get("tickets", record_id)
    records = db.scalars(
        select(TicketMessage)
        .where(TicketMessage.org_id == user.org_id, TicketMessage.ticket_id == record_id)
        .order_by(TicketMessage.created_at)
    )
    return {
        "items": [
            {
                **service.serialize(record),
                "delivery_status": "internal" if record.internal else "draft",
            }
            for record in records
        ]
    }


@router.post("/tickets/{record_id}/messages", status_code=201)
def ticket_message(
    record_id: str,
    payload: MessageInput,
    db: SessionDep,
    user: CurrentUser,
    idempotency_key: str | None = Header(default=None),
) -> dict[str, Any]:
    return service.post_ticket_message(db, user, record_id, payload, idempotency_key)


@router.post("/activities/{record_id}/complete")
def complete_activity(record_id: str, db: SessionDep, user: CurrentUser) -> dict[str, Any]:
    record = service.modify(db, user, "activities", record_id, {"status": "completed"})
    db.commit()
    return service.serialize(record)


@router.get("/{entity}/export")
def export_records(
    entity: str,
    db: SessionDep,
    user: CurrentUser,
    q: str = "",
    status: str | None = None,
    owner_id: str | None = None,
    stage_id: str | None = None,
    pipeline_id: str | None = None,
    sort: str = "created_at",
    order: Literal["asc", "desc"] = "asc",
) -> Response:
    content = service.export_csv(
        db,
        user,
        entity,
        q=q,
        status=status,
        owner_id=owner_id,
        stage_id=stage_id,
        pipeline_id=pipeline_id,
        sort=sort,
        order=order,
    )
    return Response(
        content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{entity}.csv"'},
    )


@router.post("/{entity}/import")
def import_records(
    entity: str, payload: CSVImport, db: SessionDep, user: CurrentUser
) -> dict[str, Any]:
    result = service.import_csv(db, user, entity, payload.csv, payload.mode)
    db.commit()
    return result


@router.get("/{entity}/{record_id}/timeline")
def timeline(entity: str, record_id: str, db: SessionDep, user: CurrentUser) -> dict[str, Any]:
    return service.record_timeline(db, user, entity, record_id)


@router.get("/demo/status")
def demo_status(db: SessionDep, user: CurrentUser) -> dict[str, Any]:
    from app.modules.crm.models import Lead

    found = db.scalar(select(Lead.id).where(Lead.org_id == user.org_id, Lead.tags.contains("demo")))
    return {"seeded": found is not None, "fictional": True}


@router.post("/demo/seed")
def demo_seed(db: SessionDep, user: CurrentUser) -> dict[str, Any]:
    from app.modules.crm.models import IdempotencyRecord
    from app.modules.crm.seed import seed_demo

    if user.role not in {"Owner", "Admin"}:
        raise HTTPException(403, "Only an owner or administrator can add demo data.")
    existing = db.scalar(
        select(IdempotencyRecord).where(
            IdempotencyRecord.org_id == user.org_id,
            IdempotencyRecord.route == "demo/seed",
            IdempotencyRecord.key == "fictional-demo-v1",
        )
    )
    if existing:
        return {"seeded": True, "already_seeded": True, "fictional": True}
    marker = IdempotencyRecord(
        org_id=user.org_id,
        route="demo/seed",
        key="fictional-demo-v1",
        payload_hash="demo-v1",
        response={},
    )
    db.add(marker)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        return {"seeded": True, "already_seeded": True, "fictional": True}
    seed_demo(db, user)
    result = {"seeded": True, "already_seeded": False, "fictional": True}
    marker.response = result
    db.commit()
    return result


@router.get("/{entity}")
def list_records(
    entity: str,
    db: SessionDep,
    user: CurrentUser,
    q: str = Query(default="", max_length=200),
    status: str | None = None,
    owner_id: str | None = None,
    stage_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    sort: str = "updated_at",
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
    entity_type: str | None = None,
    entity_id: str | None = None,
    pipeline_id: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict[str, Any]:
    rows, total = CRMRepository(db, user).list(
        entity,
        q=q,
        status=status,
        owner_id=owner_id,
        stage_id=stage_id,
        limit=limit,
        offset=offset,
        sort=sort,
        order=order,
        entity_type=entity_type,
        entity_id=entity_id,
        pipeline_id=pipeline_id,
        date_from=date_from,
        date_to=date_to,
    )
    return {
        "items": [service.serialize(row) for row in rows],
        "total": total,
        "page": offset // limit + 1,
        "page_size": limit,
    }


@router.post("/{entity}", status_code=201)
def create_record(
    entity: str,
    db: SessionDep,
    user: CurrentUser,
    payload: Annotated[dict[str, Any], Body()],
    idempotency_key: str | None = Header(default=None),
) -> dict[str, Any]:
    require_write(user)
    route = f"{user.id}/{entity}"
    previous, digest = service.idempotent_result(db, user, idempotency_key, route, payload)
    if previous:
        CRMRepository(db, user).get(entity, previous["id"])
        return previous
    try:
        record = service.create(db, user, entity, payload)
        result = service.serialize(record)
        service.remember(db, user, idempotency_key, route, digest, result)
        db.commit()
    except IntegrityError:
        db.rollback()
        previous, _ = service.idempotent_result(db, user, idempotency_key, route, payload)
        if previous:
            CRMRepository(db, user).get(entity, previous["id"])
            return previous
        raise HTTPException(
            409, "This record conflicts with existing data. Refresh and retry."
        ) from None
    return result


@router.get("/{entity}/{record_id}")
def get_record(entity: str, record_id: str, db: SessionDep, user: CurrentUser) -> dict[str, Any]:
    return service.serialize(CRMRepository(db, user).get(entity, record_id))


@router.patch("/{entity}/{record_id}")
def update_record(
    entity: str,
    record_id: str,
    db: SessionDep,
    user: CurrentUser,
    payload: Annotated[dict[str, Any], Body()],
) -> dict[str, Any]:
    record = service.modify(db, user, entity, record_id, payload)
    db.commit()
    return service.serialize(record)


@router.delete("/{entity}/{record_id}", status_code=204)
def delete_record(entity: str, record_id: str, db: SessionDep, user: CurrentUser) -> Response:
    service.archive_record(db, user, entity, record_id)
    db.commit()
    return Response(status_code=204)
