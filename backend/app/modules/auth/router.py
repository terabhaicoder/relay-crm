from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response

from app.core.auth import CurrentUser, SessionDep
from app.core.limits import limit_identity
from app.modules.auth import service
from app.modules.auth.schemas import (
    InviteAccept,
    InviteCreate,
    LoginRequest,
    PasswordChange,
    ProfileUpdate,
    SignupRequest,
    TeamCreate,
    TeamUpdate,
    UserResponse,
)

router = APIRouter(tags=["authentication"])


@router.get("/auth/options")
def auth_options(request: Request) -> dict[str, bool]:
    return {"signup_enabled": request.app.state.settings.signup_enabled}


def set_session_cookie(response: Response, token: str, request: Request) -> None:
    settings = request.app.state.settings
    response.set_cookie(
        "erp_session",
        token,
        httponly=True,
        samesite="lax",
        secure=settings.environment == "production",
        path="/",
        max_age=settings.session_days * 86400,
    )


@router.post("/auth/signup", response_model=UserResponse, status_code=201)
def signup(
    payload: SignupRequest, request: Request, response: Response, db: SessionDep
) -> UserResponse:
    if not request.app.state.settings.signup_enabled:
        raise HTTPException(
            403, "Public signup is disabled. Ask your administrator for an invitation."
        )
    limit_identity(request, payload.email)
    user = service.create_account(db, payload)
    token = service.issue_session(db, user, request.app.state.settings.session_days)
    db.commit()
    set_session_cookie(response, token, request)
    return service.user_response(db, user)


@router.post("/auth/login", response_model=UserResponse)
def login(
    payload: LoginRequest, request: Request, response: Response, db: SessionDep
) -> UserResponse:
    limit_identity(request, payload.email)
    user = service.authenticate(db, payload.email, payload.password)
    token = service.issue_session(db, user, request.app.state.settings.session_days)
    db.commit()
    set_session_cookie(response, token, request)
    return service.user_response(db, user)


@router.post("/auth/logout", status_code=204)
def logout(request: Request, response: Response, db: SessionDep) -> None:
    service.revoke_session(db, request.cookies.get("erp_session"))
    response.delete_cookie("erp_session", path="/")


@router.get("/auth/me", response_model=UserResponse)
@router.get("/me", response_model=UserResponse)
def me(user: CurrentUser, db: SessionDep) -> UserResponse:
    return service.user_response(db, user)


@router.get("/team", response_model=list[UserResponse])
def team(user: CurrentUser, db: SessionDep) -> list[UserResponse]:
    return service.list_team(db, user)


@router.post("/team", response_model=UserResponse, status_code=201)
def add_teammate(payload: TeamCreate, user: CurrentUser, db: SessionDep) -> UserResponse:
    return service.user_response(db, service.add_team_member(db, user, payload))


@router.patch("/me", response_model=UserResponse)
def profile(payload: ProfileUpdate, user: CurrentUser, db: SessionDep) -> UserResponse:
    return service.update_profile(db, user, payload.name)


@router.post("/auth/logout-all", status_code=204)
def logout_everywhere(user: CurrentUser, db: SessionDep, response: Response) -> None:
    service.logout_all(db, user)
    response.delete_cookie("erp_session", path="/")


@router.post("/auth/change-password", response_model=UserResponse)
def password_change(
    payload: PasswordChange, user: CurrentUser, db: SessionDep, request: Request, response: Response
) -> UserResponse:
    limit_identity(request, "password:" + user.id)
    token = service.change_password(
        db,
        user,
        payload.current_password,
        payload.new_password,
        request.app.state.settings.session_days,
    )
    set_session_cookie(response, token, request)
    return service.user_response(db, user)


@router.post("/team/invites", status_code=201)
def invite(payload: InviteCreate, user: CurrentUser, db: SessionDep) -> dict[str, Any]:
    return service.create_invite(db, user, payload)


@router.get("/auth/invites/{token}")
def invitation_details(token: str, db: SessionDep) -> dict[str, str]:
    return service.invite_details(db, token)


@router.post("/auth/accept-invite", response_model=UserResponse, status_code=201)
def accept_invitation(
    payload: InviteAccept, request: Request, response: Response, db: SessionDep
) -> UserResponse:
    limit_identity(request, "invite:" + payload.token)
    user, token = service.accept_invite(db, payload, request.app.state.settings.session_days)
    set_session_cookie(response, token, request)
    return service.user_response(db, user)


@router.patch("/team/{member_id}", response_model=UserResponse)
def member_update(
    member_id: str, payload: TeamUpdate, user: CurrentUser, db: SessionDep
) -> UserResponse:
    return service.update_member(db, user, member_id, payload)


@router.get("/auth/sessions")
def sessions(request: Request, user: CurrentUser, db: SessionDep) -> list[dict[str, Any]]:
    return service.active_sessions(db, user, request.cookies.get("erp_session"))


@router.delete("/auth/sessions/{session_id}", status_code=204)
def revoke_active_session(session_id: str, user: CurrentUser, db: SessionDep) -> None:
    service.revoke_session_by_id(db, user, session_id)
