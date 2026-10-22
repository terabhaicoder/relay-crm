from typing import Any, Literal

from fastapi import APIRouter, Header, HTTPException, Query
from sqlalchemy import func, select

from app.core.auth import CurrentUser, SessionDep, require_write
from app.modules.engagement import service, workflows
from app.modules.engagement.models import (
    EmailDraft,
    EmailTemplate,
    Notification,
)
from app.modules.engagement.schemas import (
    AutomationInput,
    AutomationJobList,
    AutomationJobResponse,
    AutomationRunList,
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
    enabled: bool | None = None,
) -> dict[str, Any]:
    return service.list_engagement(
        db,
        user,
        "automations",
        q=q,
        sort=sort,
        order=order,
        limit=limit,
        offset=offset,
        enabled=enabled,
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
    return service.update_automation(db, user, record_id, body.model_dump())


@router.get("/automations/runs", response_model=AutomationRunList)
def runs(
    db: SessionDep,
    user: CurrentUser,
    q: str = Query(default="", max_length=200),
    rule_id: str | None = None,
    status: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    return workflows.history(
        db,
        user,
        jobs=False,
        q=q,
        rule_id=rule_id,
        status=status,
        entity_type=entity_type,
        entity_id=entity_id,
        limit=limit,
        offset=offset,
    )


@router.get("/automations/jobs", response_model=AutomationJobList)
def jobs(
    db: SessionDep,
    user: CurrentUser,
    q: str = Query(default="", max_length=200),
    rule_id: str | None = None,
    status: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    return workflows.history(
        db,
        user,
        jobs=True,
        q=q,
        rule_id=rule_id,
        status=status,
        entity_type=entity_type,
        entity_id=entity_id,
        limit=limit,
        offset=offset,
    )


@router.post("/automations/jobs/{record_id}/retry", response_model=AutomationJobResponse)
def retry_job(record_id: str, db: SessionDep, user: CurrentUser) -> dict[str, Any]:
    return workflows.manage_job(db, user, record_id, "retry")


@router.post("/automations/jobs/{record_id}/cancel", response_model=AutomationJobResponse)
def cancel_job(record_id: str, db: SessionDep, user: CurrentUser) -> dict[str, Any]:
    return workflows.manage_job(db, user, record_id, "cancel")


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
    entity_type: str | None = Query(default=None, max_length=30),
    entity_id: str | None = Query(default=None, max_length=36),
) -> dict[str, Any]:
    return service.list_engagement(
        db,
        user,
        "email/messages",
        q=q,
        sort=sort,
        order=order,
        limit=limit,
        offset=offset,
        entity_type=entity_type,
        entity_id=entity_id,
    )


@router.post("/email/messages", status_code=201)
def create_draft(
    body: DraftInput,
    db: SessionDep,
    user: CurrentUser,
    idempotency_key: str | None = Header(default=None),
) -> dict[str, Any]:
    return service.create_engagement(db, user, "email/messages", body.model_dump(), idempotency_key)


@router.get("/email/messages/{record_id}")
def get_draft(record_id: str, db: SessionDep, user: CurrentUser) -> dict[str, Any]:
    row = db.scalar(
        select(EmailDraft).where(EmailDraft.org_id == user.org_id, EmailDraft.id == record_id)
    )
    if row is None or (
        user.role in {"Sales Rep", "Sales Representative"} and row.owner_id != user.id
    ):
        raise HTTPException(404)
    return encode(row)


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
    values = body.model_dump(exclude_unset=True)
    linked_type = values.get("entity_type", row.entity_type)
    linked_id = values.get("entity_id", row.entity_id)
    if linked_type or linked_id:
        from app.modules.crm.repository import CRMRepository

        if not linked_type or not linked_id:
            raise HTTPException(422, "Choose a valid linked record.")
        if linked_type != row.entity_type or linked_id != row.entity_id:
            CRMRepository(db, user).get(linked_type, linked_id)
    for key, value in values.items():
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
