from typing import Annotated, Any

from fastapi import APIRouter, Header, Query

from app.core.auth import CurrentUser, SessionDep
from app.modules.customization import service
from app.modules.customization.schemas import (
    CustomDefinitionCreate,
    CustomDefinitionList,
    CustomDefinitionResponse,
    CustomDefinitionUpdate,
    CustomEntity,
    CustomRecordResponse,
    CustomValuesUpdate,
)

router = APIRouter(prefix="/custom-fields", tags=["Custom fields"])
Key = Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=200)]


@router.get("/definitions", response_model=CustomDefinitionList)
def definitions(
    db: SessionDep,
    user: CurrentUser,
    entity: CustomEntity,
    include_archived: bool = False,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    return service.definitions(db, user, entity, include_archived, limit, offset)


@router.post("/definitions", response_model=CustomDefinitionResponse, status_code=201)
def create_definition(
    payload: CustomDefinitionCreate, db: SessionDep, user: CurrentUser, idempotency_key: Key
) -> dict[str, Any]:
    return service.create_definition(db, user, payload, idempotency_key)


@router.patch("/definitions/{field_id}", response_model=CustomDefinitionResponse)
def update_definition(
    field_id: str, payload: CustomDefinitionUpdate, db: SessionDep, user: CurrentUser
) -> dict[str, Any]:
    return service.update_definition(db, user, field_id, payload)


@router.get("/records/{entity}/{record_id}", response_model=CustomRecordResponse)
def record(
    entity: CustomEntity, record_id: str, db: SessionDep, user: CurrentUser
) -> dict[str, Any]:
    return service.record(db, user, entity, record_id)


@router.patch("/records/{entity}/{record_id}", response_model=CustomRecordResponse)
def save_record(
    entity: CustomEntity,
    record_id: str,
    payload: CustomValuesUpdate,
    db: SessionDep,
    user: CurrentUser,
    idempotency_key: Key,
) -> dict[str, Any]:
    return service.save_record(db, user, entity, record_id, payload, idempotency_key)
