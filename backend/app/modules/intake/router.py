from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException, Query, Request

from app.core.auth import CurrentUser, SessionDep
from app.modules.intake import service
from app.modules.intake.schemas import (
    FormInput,
    FormList,
    FormResponse,
    PublicForm,
    Receipt,
    SubmissionInput,
    SubmissionList,
)

router = APIRouter(tags=["Lead capture"])


@router.get("/capture-forms", response_model=FormList)
def listing(
    db: SessionDep,
    user: CurrentUser,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    return service.listing(db, user, limit, offset)


@router.post("/capture-forms", status_code=201, response_model=FormResponse)
def create(
    payload: FormInput,
    db: SessionDep,
    user: CurrentUser,
    idempotency_key: Annotated[str, Header(min_length=1, max_length=200)],
) -> dict[str, Any]:
    return service.create(db, user, payload, idempotency_key)


@router.patch("/capture-forms/{record_id}", response_model=FormResponse)
def update(record_id: str, payload: FormInput, db: SessionDep, user: CurrentUser) -> dict[str, Any]:
    return service.update(db, user, record_id, payload)


@router.get("/capture-forms/{record_id}/submissions", response_model=SubmissionList)
def submissions(
    record_id: str,
    db: SessionDep,
    user: CurrentUser,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    return service.submissions(db, user, record_id, limit, offset)


@router.get("/public/forms/{record_id}", response_model=PublicForm)
def public_details(record_id: str, db: SessionDep) -> dict[str, Any]:
    return service.public_details(db, record_id)


@router.post("/public/forms/{record_id}", status_code=201, response_model=Receipt)
def submit(
    record_id: str,
    payload: SubmissionInput,
    request: Request,
    db: SessionDep,
    idempotency_key: Annotated[str, Header(min_length=1, max_length=200)],
) -> dict[str, Any]:
    peer = request.client.host if request.client else "unknown"
    if not request.app.state.intake_limiter.allow(f"capture:{peer}", 30):
        raise HTTPException(
            429, "Too many inquiries. Please wait one minute.", headers={"Retry-After": "60"}
        )
    return service.submit(db, record_id, payload, idempotency_key)
