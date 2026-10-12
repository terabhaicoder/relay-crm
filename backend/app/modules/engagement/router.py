from typing import Any, Literal

from fastapi import APIRouter, Header, HTTPException, Query
from sqlalchemy import func, or_, select

from app.core.auth import CurrentUser, SessionDep, require_write
from app.modules.engagement import service
from app.modules.engagement.models import (
    Automation,
    AutomationRun,
    EmailDraft,
    EmailTemplate,
    Notification,
)
from app.modules.engagement.schemas import (
    AutomationInput,
    AutomationToggle,
    DraftInput,
    TemplateInput,
)

router = APIRouter(tags=["Engagement"])


def encode(record: Any) -> dict[str, Any]:
    return {column.name: getattr(record, column.name) for column in record.__table__.columns}


@router.get("/automations")
def automations(
    db: SessionDep,
    user: CurrentUser,
    q: str = Query(default="", max_length=200),
    sort: str = "created_at",
    order: Literal["asc", "desc"] = "desc",
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    return service.list_engagement(
        db, user, "automations", q=q, sort=sort, order=order, limit=limit, offset=offset
    )


@router.post("/automations", status_code=201)
def create_automation(
    body: AutomationInput,
    db: SessionDep,
    user: CurrentUser,
    idempotency_key: str | None = Header(default=None),
) -> dict[str, Any]:
    return service.create_engagement(db, user, "automations", body.model_dump(), idempotency_key)


@router.patch("/automations/{record_id}")
def toggle_automation(
    record_id: str, body: AutomationInput | AutomationToggle, db: SessionDep, user: CurrentUser
) -> dict[str, Any]:
    require_write(user)
    if user.role not in {"Owner", "Admin", "Sales Manager"}:
        raise HTTPException(403, "Only managers can configure automations.")
    row = db.scalar(
        select(Automation).where(Automation.org_id == user.org_id, Automation.id == record_id)
    )
    if row is None:
        raise HTTPException(404)
    for key, value in body.model_dump().items():
        setattr(row, key, value)
    db.commit()
    return encode(row)


@router.get("/automations/runs")
def runs(db: SessionDep, user: CurrentUser) -> dict[str, Any]:
    from app.modules.crm.repository import MODELS, CRMRepository

    query = select(AutomationRun).where(AutomationRun.org_id == user.org_id)
    if user.role in {"Sales Rep", "Sales Representative"}:
        repository = CRMRepository(db, user)
        allowed = [
            (
                (AutomationRun.entity_type == entity)
                & select(model.id)
                .where(model.id == AutomationRun.entity_id, *repository.scope(model))
                .exists()
            )
            for entity in MODELS
            for model in [repository.model(entity)]
        ]
        query = query.where(or_(*allowed))
    rows = db.scalars(query.order_by(AutomationRun.created_at.desc()).limit(100)).all()
    return {"items": [encode(row) for row in rows]}


@router.get("/notifications")
def notifications(
    db: SessionDep, user: CurrentUser, limit: int = Query(30, ge=1, le=100)
) -> dict[str, Any]:
    scope = (Notification.org_id == user.org_id, Notification.user_id == user.id)
    rows = db.scalars(
        select(Notification).where(*scope).order_by(Notification.created_at.desc()).limit(limit)
    ).all()
    unread = db.scalar(
        select(func.count()).select_from(Notification).where(*scope, Notification.read.is_(False))
    )
    return {"items": [encode(row) for row in rows], "unread": unread}


@router.post("/notifications/{record_id}/read")
def mark_read(record_id: str, db: SessionDep, user: CurrentUser) -> dict[str, Any]:
    row = db.scalar(
        select(Notification).where(
            Notification.org_id == user.org_id,
            Notification.user_id == user.id,
            Notification.id == record_id,
        )
    )
    if row is None:
        raise HTTPException(404)
    row.read = True
    db.commit()
    return encode(row)


@router.get("/email/templates")
def templates(db: SessionDep, user: CurrentUser) -> dict[str, Any]:
    rows = db.scalars(
        select(EmailTemplate)
        .where(EmailTemplate.org_id == user.org_id)
        .order_by(EmailTemplate.created_at.desc())
        .limit(100)
    ).all()
    return {"items": [encode(row) for row in rows]}


@router.post("/email/templates", status_code=201)
def create_template(
    body: TemplateInput,
    db: SessionDep,
    user: CurrentUser,
    idempotency_key: str | None = Header(default=None),
) -> dict[str, Any]:
    return service.create_engagement(
        db, user, "email/templates", body.model_dump(), idempotency_key
    )


@router.delete("/email/templates/{record_id}", status_code=204)
def delete_template(record_id: str, db: SessionDep, user: CurrentUser) -> None:
    require_write(user)
    row = db.scalar(
        select(EmailTemplate).where(
            EmailTemplate.org_id == user.org_id, EmailTemplate.id == record_id
        )
    )
    if row is None:
        raise HTTPException(404)
    db.delete(row)
    db.commit()


@router.patch("/email/templates/{record_id}")
def update_template(
    record_id: str, body: TemplateInput, db: SessionDep, user: CurrentUser
) -> dict[str, Any]:
    require_write(user)
    row = db.scalar(
        select(EmailTemplate).where(
            EmailTemplate.org_id == user.org_id, EmailTemplate.id == record_id
        )
    )
    if row is None:
        raise HTTPException(404)
    for key, value in body.model_dump().items():
        setattr(row, key, value)
    db.commit()
    return encode(row)


@router.get("/email/messages")
def drafts(
    db: SessionDep,
    user: CurrentUser,
    q: str = Query(default="", max_length=200),
    sort: str = "created_at",
    order: Literal["asc", "desc"] = "desc",
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    return service.list_engagement(
        db, user, "email/messages", q=q, sort=sort, order=order, limit=limit, offset=offset
    )


@router.post("/email/messages", status_code=201)
def create_draft(
    body: DraftInput,
    db: SessionDep,
    user: CurrentUser,
    idempotency_key: str | None = Header(default=None),
) -> dict[str, Any]:
    return service.create_engagement(db, user, "email/messages", body.model_dump(), idempotency_key)


@router.post("/email/messages/{record_id}/send")
def send_draft(record_id: str, db: SessionDep, user: CurrentUser) -> None:
    require_write(user)
    row = db.scalar(
        select(EmailDraft).where(EmailDraft.org_id == user.org_id, EmailDraft.id == record_id)
    )
    if row is None:
        raise HTTPException(404)
    if user.role in {"Sales Rep", "Sales Representative"} and row.owner_id != user.id:
        raise HTTPException(404)
    # User explicitly deferred Gmail connection. Never claim a provider side effect.
    raise HTTPException(
        409, "Gmail is not connected. Your draft is saved; connect Gmail before sending."
    )


@router.patch("/email/messages/{record_id}")
def update_draft(
    record_id: str, body: DraftInput, db: SessionDep, user: CurrentUser
) -> dict[str, Any]:
    require_write(user)
    row = db.scalar(
        select(EmailDraft).where(EmailDraft.org_id == user.org_id, EmailDraft.id == record_id)
    )
    if row is None or (
        user.role in {"Sales Rep", "Sales Representative"} and row.owner_id != user.id
    ):
        raise HTTPException(404)
    if row.status != "draft":
        raise HTTPException(409, "Only drafts can be edited.")
    if body.entity_type or body.entity_id:
        from app.modules.crm.repository import CRMRepository

        if not body.entity_type or not body.entity_id:
            raise HTTPException(422, "Choose a valid linked record.")
        CRMRepository(db, user).get(body.entity_type, body.entity_id)
    for key, value in body.model_dump().items():
        setattr(row, key, value)
    db.commit()
    return encode(row)


@router.delete("/email/messages/{record_id}", status_code=204)
def delete_draft(record_id: str, db: SessionDep, user: CurrentUser) -> None:
    require_write(user)
    row = db.scalar(
        select(EmailDraft).where(EmailDraft.org_id == user.org_id, EmailDraft.id == record_id)
    )
    if row is None or (
        user.role in {"Sales Rep", "Sales Representative"} and row.owner_id != user.id
    ):
        raise HTTPException(404)
    if row.status != "draft":
        raise HTTPException(409, "Only unsent drafts can be deleted.")
    db.delete(row)
    db.commit()


@router.get("/integrations")
def integrations(user: CurrentUser) -> dict[str, Any]:
    del user
    return {
        "items": [
            {
                "id": "gmail",
                "name": "Gmail",
                "status": "not_connected",
                "description": "Connection deferred. Email templates and drafts are available now.",
                "setup_required": [
                    "Google OAuth client",
                    "Verified callback URL",
                    "Mailbox consent",
                ],
            }
        ]
    }
