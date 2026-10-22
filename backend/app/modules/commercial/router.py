from typing import Annotated, Literal

from fastapi import APIRouter, Header, Query

from app.core.auth import CurrentUser, SessionDep
from app.modules.commercial import service
from app.modules.commercial.schemas import (
    QuoteCreate,
    QuoteEdit,
    QuoteList,
    QuoteResponse,
    QuoteTransition,
)

router = APIRouter(prefix="/quotations", tags=["quotations"])
Key = Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=200)]


@router.get("", response_model=QuoteList)
def list_quotations(
    db: SessionDep,
    user: CurrentUser,
    q: str = Query(default="", max_length=200),
    status: Literal["draft", "issued", "accepted", "declined"] | None = None,
    deal_id: str | None = None,
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
) -> dict[str, object]:
    return service.listing(db, user, q, status, deal_id, limit, offset)


@router.post("", response_model=QuoteResponse, status_code=201)
def create_quotation(
    payload: QuoteCreate, db: SessionDep, user: CurrentUser, idempotency_key: Key
) -> dict[str, object]:
    return service.create(db, user, payload, idempotency_key)


@router.get("/{quote_id}", response_model=QuoteResponse)
def get_quotation(quote_id: str, db: SessionDep, user: CurrentUser) -> dict[str, object]:
    return service.detail(db, user, quote_id)


@router.patch("/{quote_id}", response_model=QuoteResponse)
def edit_quotation(
    quote_id: str, payload: QuoteEdit, db: SessionDep, user: CurrentUser
) -> dict[str, object]:
    return service.edit(db, user, quote_id, payload)


@router.post("/{quote_id}/{action}", response_model=QuoteResponse)
def transition_quotation(
    quote_id: str,
    action: Literal["issue", "accept", "decline"],
    payload: QuoteTransition,
    db: SessionDep,
    user: CurrentUser,
    idempotency_key: Key,
) -> dict[str, object]:
    return service.transition(db, user, quote_id, action, payload, idempotency_key)
