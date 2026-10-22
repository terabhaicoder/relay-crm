from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.auth import require_write
from app.core.db import ensure_write_transaction
from app.modules.auth.models import User, utcnow
from app.modules.commercial.models import Quotation, QuotationEvent, QuotationLine
from app.modules.commercial.repository import QuotationRepository
from app.modules.commercial.schemas import QuoteCreate, QuoteEdit, QuoteFields, QuoteTransition
from app.modules.crm import service as crm_service

CENT = Decimal("0.01")
MAX_TOTAL = Decimal("999999999999.99")


def validate_crm_change(
    db: Session,
    user: User,
    entity: str,
    record_id: str,
    changes: dict[str, Any] | None,
) -> None:
    """Keep commercial history linked while CRM owns all master mutations."""
    reference = {
        "deals": Quotation.deal_id,
        "parties": Quotation.party_id,
        "contacts": Quotation.contact_id,
    }.get(entity)
    if reference is None:
        return
    if changes is not None:
        guarded = {"party_id", "contact_id"} if entity == "deals" else {"party_id"}
        if entity == "parties" or not guarded.intersection(changes):
            return
    # Check every quotation in this org, including colleagues' records. The
    # caller has already checked authority to edit the original CRM record.
    linked = db.scalar(
        select(Quotation.id).where(Quotation.org_id == user.org_id, reference == record_id).limit(1)
    )
    if linked:
        raise HTTPException(
            409,
            "This record has quotation history. Keep its customer links and record intact.",
        )


def today() -> str:
    return datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat()


def stamp(value: datetime | None) -> str | None:
    return value.isoformat() + ("+00:00" if value.tzinfo is None else "") if value else None


def detail(db: Session, user: User, quote_id: str) -> dict[str, Any]:
    row = QuotationRepository(db, user).quote(quote_id)
    result = {
        column.name: getattr(row, column.name)
        for column in row.__table__.columns
        if column.name not in {"org_id", "created_by", "updated_by"}
    }
    for field in ("subtotal", "discount", "total"):
        result[field] = format(result[field], ".2f")
    for field in ("created_at", "updated_at", "issued_at", "decided_at"):
        result[field] = stamp(result[field])
    lines = db.scalars(
        select(QuotationLine)
        .where(QuotationLine.org_id == user.org_id, QuotationLine.quotation_id == row.id)
        .order_by(QuotationLine.position)
    )
    result["lines"] = [
        {
            "id": line.id,
            "description": line.description,
            "quantity": format(line.quantity, ".3f"),
            "unit_price": format(line.unit_price, ".4f"),
            "amount": format(line.amount, ".2f"),
        }
        for line in lines
    ]
    events = db.scalars(
        select(QuotationEvent)
        .where(QuotationEvent.org_id == user.org_id, QuotationEvent.quotation_id == row.id)
        .order_by(QuotationEvent.created_at.desc(), QuotationEvent.id)
        .limit(100)
    )
    result["events"] = [
        {
            "action": event.action,
            "actor_id": event.actor_id,
            "created_at": stamp(event.created_at),
            "changes": event.changes,
        }
        for event in events
    ]
    return result


def listing(
    db: Session,
    user: User,
    q: str,
    status: str | None,
    deal_id: str | None,
    limit: int,
    offset: int,
) -> dict[str, Any]:
    repo = QuotationRepository(db, user)
    query = repo.quotes()
    if deal_id:
        repo.get("deals", deal_id)
        query = query.where(Quotation.deal_id == deal_id)
    if status:
        query = query.where(Quotation.status == status)
    if q:
        escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(Quotation.name.ilike(f"%{escaped}%", escape="\\"))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(Quotation.updated_at.desc(), Quotation.id).offset(offset).limit(limit)
    ).all()
    return {"items": [detail(db, user, row.id) for row in rows], "total": total}


def totals(payload: QuoteFields) -> tuple[Decimal, Decimal, list[Decimal]]:
    amounts = [
        (line.quantity * line.unit_price).quantize(CENT, rounding=ROUND_HALF_UP)
        for line in payload.lines
    ]
    subtotal = sum(amounts, Decimal("0.00"))
    if subtotal > MAX_TOTAL:
        raise HTTPException(422, "Quotation exceeds the supported monetary limit.")
    if payload.discount > subtotal:
        raise HTTPException(422, "Discount cannot exceed the subtotal.")
    return subtotal, subtotal - payload.discount, amounts


def write_lines(db: Session, user: User, row: Quotation, payload: QuoteFields) -> None:
    subtotal, total, amounts = totals(payload)
    row.name, row.terms = payload.name, payload.terms
    row.valid_until = payload.valid_until.isoformat() if payload.valid_until else None
    row.subtotal, row.discount, row.total = subtotal, payload.discount, total
    db.execute(
        delete(QuotationLine).where(
            QuotationLine.org_id == user.org_id, QuotationLine.quotation_id == row.id
        )
    )
    for position, (line, amount) in enumerate(zip(payload.lines, amounts, strict=True)):
        db.add(
            QuotationLine(
                org_id=user.org_id,
                quotation_id=row.id,
                position=position,
                description=line.description,
                quantity=line.quantity,
                unit_price=line.unit_price,
                amount=amount,
            )
        )


def audit(
    db: Session, user: User, row: Quotation, action: str, changes: dict[str, str | bool]
) -> None:
    db.add(
        QuotationEvent(
            org_id=user.org_id,
            quotation_id=row.id,
            actor_id=user.id,
            action=action,
            changes=changes,
        )
    )


def create(db: Session, user: User, payload: QuoteCreate, key: str) -> dict[str, Any]:
    require_write(user)
    ensure_write_transaction(db)
    repo = QuotationRepository(db, user)

    def action() -> dict[str, Any]:
        deal = repo.get("deals", payload.deal_id)
        party = repo.get("parties", deal.party_id) if deal.party_id else None
        contact = repo.get("contacts", deal.contact_id) if deal.contact_id else None
        if not party and not contact:
            raise HTTPException(422, "Link a company or contact to the deal before quoting.")
        if deal.status != "open":
            raise HTTPException(409, "Create quotations for an open deal.")
        subtotal, total, _ = totals(payload)
        row = Quotation(
            org_id=user.org_id,
            deal_id=deal.id,
            party_id=deal.party_id,
            contact_id=deal.contact_id,
            name=payload.name,
            customer_name=party.name if party else contact.name if contact else "",
            contact_name=contact.name if contact else "",
            deal_name=deal.name,
            subtotal=subtotal,
            total=total,
            created_by=user.id,
            updated_by=user.id,
        )
        db.add(row)
        db.flush()
        write_lines(db, user, row, payload)
        audit(db, user, row, "created", {"total": str(total)})
        db.flush()
        return detail(db, user, row.id)

    return crm_service.execute_idempotent(
        db,
        user,
        key,
        f"{user.id}/quotations",
        payload.model_dump(mode="json"),
        action,
        lambda previous: detail(db, user, previous["id"]),
    )


def edit(db: Session, user: User, quote_id: str, payload: QuoteEdit) -> dict[str, Any]:
    require_write(user)
    ensure_write_transaction(db)
    row = QuotationRepository(db, user).quote(quote_id)
    if row.status != "draft":
        raise HTTPException(409, "Issued quotation terms are locked. Create a new quotation.")
    if row.version != payload.version:
        raise HTTPException(409, "This quotation changed. Refresh before saving.")
    write_lines(db, user, row, payload)
    row.version += 1
    row.updated_at, row.updated_by = utcnow(), user.id
    audit(db, user, row, "updated", {"total": str(row.total)})
    db.flush()
    result = detail(db, user, row.id)
    db.commit()
    return result


def transition(
    db: Session, user: User, quote_id: str, action: str, payload: QuoteTransition, key: str
) -> dict[str, Any]:
    require_write(user)
    ensure_write_transaction(db)
    repo = QuotationRepository(db, user)

    def apply() -> dict[str, Any]:
        row = repo.quote(quote_id)
        if row.version != payload.version:
            raise HTTPException(409, "This quotation changed. Refresh before continuing.")
        expected = "draft" if action == "issue" else "issued"
        if row.status != expected:
            raise HTTPException(409, f"Only {expected} quotations can be {action}d.")
        if action in {"issue", "accept"} and row.valid_until and row.valid_until < today():
            raise HTTPException(
                409, "Quotation has expired. Create or edit a draft with valid dates."
            )
        if action != "accept" and payload.close_deal:
            raise HTTPException(422, "Only acceptance can close a deal.")
        if action in {"accept", "decline"} and not payload.note:
            raise HTTPException(422, "Record the customer's decision or evidence reference.")
        deal = repo.get("deals", row.deal_id)
        if action == "accept" and payload.close_deal:
            if payload.deal_version is None:
                raise HTTPException(422, "Refresh the linked deal before closing it.")
            if deal.status != "open":
                raise HTTPException(409, "The linked deal is already closed. Refresh it first.")
            if (deal.party_id, deal.contact_id) != (row.party_id, row.contact_id):
                raise HTTPException(409, "The deal's customer changed. Create a new quotation.")
            crm_service.modify(
                db,
                user,
                "deals",
                deal.id,
                {"status": "won", "amount": str(row.total), "version": payload.deal_version},
            )
        row.status = {"issue": "issued", "accept": "accepted", "decline": "declined"}[action]
        row.version += 1
        row.updated_at, row.updated_by = utcnow(), user.id
        if action == "issue":
            row.issued_at = utcnow()
        else:
            row.decided_at, row.decision_note = utcnow(), payload.note
        audit(db, user, row, row.status, {"note": payload.note, "deal_closed": payload.close_deal})
        db.flush()
        return detail(db, user, row.id)

    return crm_service.execute_idempotent(
        db,
        user,
        key,
        f"{user.id}/quotations/{quote_id}/{action}",
        payload.model_dump(mode="json"),
        apply,
        lambda previous: detail(db, user, previous["id"]),
    )
