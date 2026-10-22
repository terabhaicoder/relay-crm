import hashlib
import json
from typing import Any

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.db import ensure_write_transaction
from app.modules.auth.models import Org, User, utcnow
from app.modules.crm import service as crm
from app.modules.crm.models import Lead
from app.modules.crm.repository import CRMRepository
from app.modules.intake.models import CaptureForm, CaptureSubmission
from app.modules.intake.repository import IntakeRepository
from app.modules.intake.schemas import FormInput, Receipt, SubmissionInput

MANAGERS = {"Owner", "Admin", "Sales Manager"}
READ_ONLY = {"Viewer", "Read-only", "Read-only/CA"}


def manager(user: User) -> None:
    if user.role not in MANAGERS:
        raise HTTPException(403, "Only managers can configure lead capture.")


def relink_entity(db: Session, user: User, entity: str, source_id: str, target_id: str) -> None:
    """CRM merge orchestration retains inquiry navigation without changing receipt contents."""
    if entity != "leads":
        return
    CRMRepository(db, user).get("leads", source_id)
    CRMRepository(db, user).get("leads", target_id)
    for receipt in db.scalars(
        select(CaptureSubmission).where(
            CaptureSubmission.org_id == user.org_id, CaptureSubmission.lead_id == source_id
        )
    ):
        receipt.lead_id = target_id


def encode(db: Session, user: User, row: CaptureForm) -> dict[str, Any]:
    receipts = IntakeRepository(db, user).submissions(row.id).subquery()
    total = db.scalar(select(func.count()).select_from(receipts)) or 0
    duplicates = (
        db.scalar(select(func.count()).select_from(receipts).where(receipts.c.duplicate.is_(True)))
        or 0
    )
    result = {
        field: getattr(row, field)
        for field in (
            "id",
            "name",
            "title",
            "description",
            "source",
            "enabled",
            "owner_ids",
            "version",
            "created_at",
        )
    } | {"submissions": total, "new_leads": total - duplicates, "duplicates": duplicates}
    result["created_at"] = row.created_at.isoformat()
    return result


def listing(db: Session, user: User, limit: int, offset: int) -> dict[str, Any]:
    manager(user)
    query = IntakeRepository(db, user).forms()
    return {
        "items": [
            encode(db, user, row)
            for row in db.scalars(
                query.order_by(CaptureForm.created_at.desc()).limit(limit).offset(offset)
            )
        ],
        "total": db.scalar(select(func.count()).select_from(query.subquery())) or 0,
    }


def validate_owners(db: Session, user: User, owners: list[str]) -> list[str]:
    unique = list(dict.fromkeys(owners))
    if unique:
        eligible = set(
            db.scalars(
                select(User.id).where(
                    User.org_id == user.org_id,
                    User.id.in_(unique),
                    User.is_active.is_(True),
                    User.role.not_in(READ_ONLY),
                )
            )
        )
        if eligible != set(unique):
            raise HTTPException(422, "Choose active team members who can edit leads.")
    return unique


def create(db: Session, user: User, payload: FormInput, key: str) -> dict[str, Any]:
    manager(user)
    ensure_write_transaction(db)
    owners = validate_owners(db, user, payload.owner_ids)

    def write() -> dict[str, Any]:
        row = CaptureForm(
            **payload.model_dump(exclude={"version", "owner_ids"}),
            owner_ids=owners,
            org_id=user.org_id,
            created_by=user.id,
            updated_by=user.id,
        )
        db.add(row)
        db.flush()
        return encode(db, user, row)

    return crm.execute_idempotent(
        db,
        user,
        key,
        f"{user.id}/capture-forms",
        payload.model_dump(),
        write,
        lambda previous: encode(db, user, IntakeRepository(db, user).get(previous["id"])),
    )


def update(db: Session, user: User, record_id: str, payload: FormInput) -> dict[str, Any]:
    manager(user)
    ensure_write_transaction(db)
    row = IntakeRepository(db, user).get(record_id)
    if payload.version != row.version:
        raise HTTPException(409, "This form changed. Refresh before saving.")
    owners = validate_owners(db, user, payload.owner_ids)
    for field, value in payload.model_dump(exclude={"version", "owner_ids"}).items():
        setattr(row, field, value)
    row.owner_ids = owners
    row.version += 1
    row.updated_by, row.updated_at = user.id, utcnow()
    db.flush()
    result = encode(db, user, row)
    db.commit()
    return result


def public_form(db: Session, record_id: str) -> tuple[CaptureForm, User]:
    # A random public form ID is an intentional, narrow capability. It never exposes CRM data.
    row = db.scalar(
        select(CaptureForm).where(CaptureForm.id == record_id, CaptureForm.enabled.is_(True))
    )
    if row is None:
        raise HTTPException(404, "This inquiry form is unavailable.")
    actor = db.scalar(
        select(User).where(
            User.id == row.created_by, User.org_id == row.org_id, User.is_active.is_(True)
        )
    )
    if actor is None or actor.role not in MANAGERS:
        raise HTTPException(404, "This inquiry form is unavailable.")
    return row, actor


def public_details(db: Session, record_id: str) -> dict[str, Any]:
    row, _ = public_form(db, record_id)
    organization = db.get(Org, row.org_id)
    return {
        "id": row.id,
        "title": row.title,
        "description": row.description,
        "organization": organization.name if organization else "",
    }


def submit(db: Session, record_id: str, payload: SubmissionInput, key: str) -> dict[str, Any]:
    try:
        person = payload.person()
    except ValidationError as exc:
        raise HTTPException(422, "Enter a valid email and international phone number.") from exc
    ensure_write_transaction(db)
    form, actor = public_form(db, record_id)
    repo = IntakeRepository(db, actor)
    digest = hashlib.sha256(json.dumps(payload.model_dump(), sort_keys=True).encode()).hexdigest()
    prior = db.scalar(repo.submissions(form.id).where(CaptureSubmission.request_key == key))
    if prior:
        if prior.payload_hash != digest:
            raise HTTPException(409, "This request key was already used with different data.")
        return Receipt().model_dump()
    matches = [Lead.email == person.email]
    if person.phone:
        matches.append(Lead.phone == person.phone)
    lead = db.scalar(
        CRMRepository(db, actor)
        .query("leads")
        .where(or_(*matches))
        .order_by(Lead.created_at)
        .limit(1)
    )
    duplicate = lead is not None
    if lead is None:
        active = set(
            db.scalars(
                select(User.id).where(
                    User.org_id == actor.org_id,
                    User.id.in_(form.owner_ids),
                    User.is_active.is_(True),
                    User.role.not_in(READ_ONLY),
                )
            )
        )
        owners = [owner for owner in form.owner_ids if owner in active]
        if form.owner_ids and not owners:
            raise HTTPException(
                503, "This form cannot receive inquiries right now. Please try later."
            )
        owner = owners[form.cursor % len(owners)] if owners else actor.id
        lead = crm.create(
            db,
            actor,
            "leads",
            {
                "name": person.name,
                "email": person.email,
                "phone": person.phone,
                "company": payload.company,
                "source": form.source,
                "owner_id": owner,
                "notes": payload.message,
            },
        )
        form.cursor += 1
    db.add(
        CaptureSubmission(
            org_id=actor.org_id,
            form_id=form.id,
            lead_id=lead.id,
            request_key=key,
            payload_hash=digest,
            name=person.name,
            message=payload.message,
            duplicate=duplicate,
        )
    )
    db.commit()
    return Receipt().model_dump()


def submissions(db: Session, user: User, record_id: str, limit: int, offset: int) -> dict[str, Any]:
    manager(user)
    repo = IntakeRepository(db, user)
    repo.get(record_id)
    query = repo.submissions(record_id)
    return {
        "items": [
            {
                field: getattr(row, field)
                for field in ("id", "lead_id", "name", "message", "duplicate", "created_at")
            }
            for row in db.scalars(
                query.order_by(CaptureSubmission.created_at.desc()).limit(limit).offset(offset)
            )
        ],
        "total": db.scalar(select(func.count()).select_from(query.subquery())) or 0,
    }
