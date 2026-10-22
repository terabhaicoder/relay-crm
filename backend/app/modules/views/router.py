from typing import Annotated, Any

from fastapi import APIRouter, Header, Query, Response

from app.core.auth import CurrentUser, SessionDep
from app.modules.views import service
from app.modules.views.repository import ViewRepository
from app.modules.views.schemas import Entity, ViewCreate, ViewList, ViewResponse, ViewUpdate

router = APIRouter(tags=["Saved views"])


@router.get("/saved-views", response_model=ViewList)
def listing(
    db: SessionDep,
    user: CurrentUser,
    entity: Entity,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    return service.listing(db, user, entity, limit, offset)


@router.post("/saved-views", status_code=201, response_model=ViewResponse)
def create(
    payload: ViewCreate,
    db: SessionDep,
    user: CurrentUser,
    idempotency_key: Annotated[str, Header(min_length=1, max_length=200)],
) -> dict[str, Any]:
    # These private preferences do not mutate business records: read-only users may save them.
    return service.create(db, user, payload, idempotency_key)


@router.get("/saved-views/{record_id}", response_model=ViewResponse)
def get(record_id: str, db: SessionDep, user: CurrentUser) -> dict[str, Any]:
    return service.encode(ViewRepository(db, user).get(record_id))


@router.patch("/saved-views/{record_id}", response_model=ViewResponse)
def update(
    record_id: str, payload: ViewUpdate, db: SessionDep, user: CurrentUser
) -> dict[str, Any]:
    return service.update(db, user, record_id, payload)


@router.delete("/saved-views/{record_id}", status_code=204)
def remove(record_id: str, db: SessionDep, user: CurrentUser) -> Response:
    service.remove(db, user, record_id)
    return Response(status_code=204)
