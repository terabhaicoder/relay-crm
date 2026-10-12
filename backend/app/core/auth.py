from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.db import get_session
from app.modules.auth.models import User
from app.modules.auth.service import lookup_user

SessionDep = Annotated[Session, Depends(get_session)]


def get_current_user(request: Request, db: SessionDep) -> User:
    return lookup_user(db, request.cookies.get("erp_session"))


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_write(user: User) -> None:
    if user.role in {"Read-only", "Read-only/CA", "Viewer"}:
        raise HTTPException(403, "Your role has read-only access.")
