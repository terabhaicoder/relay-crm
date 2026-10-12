import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.auth.models import Invite, LoginSession, Org, SecurityAudit, User
from app.modules.auth.schemas import (
    InviteAccept,
    InviteCreate,
    SignupRequest,
    TeamCreate,
    TeamUpdate,
    UserResponse,
)


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    # OWASP's 16 MiB scrypt profile: N=2^14, r=8, p=5.
    derived = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=5)
    return f"scrypt-v2${salt}${derived.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, salt, expected = stored.split("$")
        if algorithm not in {"scrypt", "scrypt-v2"} or len(salt) != 32 or len(expected) != 128:
            return False
        actual = hashlib.scrypt(
            password.encode(),
            salt=bytes.fromhex(salt),
            n=16384,
            r=8,
            p=5 if algorithm == "scrypt-v2" else 1,
        )
        return secrets.compare_digest(actual.hex(), expected)
    except (ValueError, TypeError):
        return False


_UNREGISTERED_PASSWORD_HASH = hash_password(secrets.token_urlsafe(32))


def create_account(db: Session, payload: SignupRequest) -> User:
    if db.scalar(select(User).where(User.email == payload.email)):
        raise HTTPException(409, "This email address is already registered.")
    org = Org(name=payload.company_name)
    db.add(org)
    db.flush()
    user = User(
        org_id=org.id,
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role="Owner",
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "This email address is already registered.") from None
    return user


def authenticate(db: Session, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email, User.is_active.is_(True)))
    valid = verify_password(password, user.password_hash if user else _UNREGISTERED_PASSWORD_HASH)
    if not user or not valid:
        raise HTTPException(401, "The email or password is incorrect.")
    if user.password_hash.startswith("scrypt$"):
        user.password_hash = hash_password(password)
    return user


def issue_session(db: Session, user: User, days: int) -> str:
    token = secrets.token_urlsafe(48)
    db.add(
        LoginSession(
            token_hash=hashlib.sha256(token.encode()).hexdigest(),
            user_id=user.id,
            org_id=user.org_id,
            expires_at=datetime.now(UTC) + timedelta(days=days),
        )
    )
    return token


def lookup_user(db: Session, token: str | None) -> User:
    if not token:
        raise HTTPException(401, "Please sign in to continue.")
    user = db.scalar(
        select(User)
        .join(LoginSession, LoginSession.user_id == User.id)
        .where(
            LoginSession.token_hash == hashlib.sha256(token.encode()).hexdigest(),
            LoginSession.expires_at > datetime.now(UTC),
            User.is_active.is_(True),
        )
    )
    if user is None:
        raise HTTPException(401, "Your session has expired. Please sign in again.")
    return user


def revoke_session(db: Session, token: str | None) -> None:
    if token:
        db.execute(
            delete(LoginSession).where(
                LoginSession.token_hash == hashlib.sha256(token.encode()).hexdigest()
            )
        )
        db.commit()


def user_response(db: Session, user: User) -> UserResponse:
    org = db.get(Org, user.org_id)
    return UserResponse(
        id=user.id,
        org_id=user.org_id,
        name=user.name,
        email=user.email,
        role=user.role,
        company_name=org.name if org else "",
        is_active=user.is_active,
    )


def list_team(db: Session, user: User) -> list[UserResponse]:
    org = db.get(Org, user.org_id)
    query = select(User).where(User.org_id == user.org_id)
    if user.role not in {"Owner", "Admin"}:
        query = query.where(User.is_active.is_(True))
    members = db.scalars(query.order_by(User.name)).all()
    return [
        UserResponse(
            id=member.id,
            org_id=member.org_id,
            name=member.name,
            email=member.email,
            role=member.role,
            company_name=org.name if org else "",
            is_active=member.is_active,
        )
        for member in members
    ]


def add_team_member(db: Session, actor: User, payload: TeamCreate) -> User:
    if actor.role not in {"Owner", "Admin"}:
        raise HTTPException(403, "Only an owner or admin can add a teammate.")
    if db.scalar(select(User).where(User.email == payload.email)):
        raise HTTPException(409, "This email address is already registered.")
    user = User(
        org_id=actor.org_id,
        name=payload.name.strip(),
        email=payload.email,
        role=payload.role,
        password_hash=hash_password(payload.password),
    )
    if not user.name:
        raise HTTPException(422, "Please enter a name.")
    db.add(user)
    try:
        db.flush()
        db.add(
            SecurityAudit(
                org_id=actor.org_id,
                actor_id=actor.id,
                action="team_member_added",
                entity_id=user.id,
            )
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "This email address is already registered.") from None
    return user


def logout_all(db: Session, user: User) -> None:
    db.execute(delete(LoginSession).where(LoginSession.user_id == user.id))
    db.commit()


def change_password(db: Session, user: User, current: str, new: str, days: int) -> str:
    if not verify_password(current, user.password_hash):
        raise HTTPException(422, "Your current password is incorrect.")
    user.password_hash = hash_password(new)
    db.execute(delete(LoginSession).where(LoginSession.user_id == user.id))
    token = issue_session(db, user, days)
    db.add(
        SecurityAudit(
            org_id=user.org_id, actor_id=user.id, action="password_changed", entity_id=user.id
        )
    )
    db.commit()
    return token


def update_profile(db: Session, user: User, name: str) -> UserResponse:
    if not name.strip():
        raise HTTPException(422, "Please enter a name.")
    user.name = name.strip()
    db.commit()
    return user_response(db, user)


def require_admin(user: User) -> None:
    if user.role not in {"Owner", "Admin"}:
        raise HTTPException(403, "Only an owner or admin can manage teammates.")


def create_invite(db: Session, actor: User, payload: InviteCreate) -> dict[str, Any]:
    require_admin(actor)
    if db.scalar(select(User).where(User.email == payload.email)):
        raise HTTPException(409, "This email address is already registered.")
    db.execute(
        delete(Invite).where(
            Invite.org_id == actor.org_id,
            Invite.email == payload.email,
            Invite.accepted_at.is_(None),
        )
    )
    token = secrets.token_urlsafe(48)
    invite = Invite(
        org_id=actor.org_id,
        email=payload.email,
        role=payload.role,
        token_hash=hashlib.sha256(token.encode()).hexdigest(),
        invited_by=actor.id,
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    db.add(invite)
    db.flush()
    db.add(
        SecurityAudit(
            org_id=actor.org_id, actor_id=actor.id, action="invite_created", entity_id=invite.id
        )
    )
    db.commit()
    return {
        "id": invite.id,
        "email": invite.email,
        "role": invite.role,
        "token": token,
        "expires_at": invite.expires_at.isoformat(),
        "delivery": "manual",
    }


def get_invite(db: Session, token: str) -> Invite:
    invite = db.scalar(
        select(Invite).where(
            Invite.token_hash == hashlib.sha256(token.encode()).hexdigest(),
            Invite.accepted_at.is_(None),
            Invite.expires_at > datetime.now(UTC),
        )
    )
    if invite is None:
        raise HTTPException(404, "This invitation is invalid or expired.")
    return invite


def invite_details(db: Session, token: str) -> dict[str, str]:
    invite = get_invite(db, token)
    org = db.get(Org, invite.org_id)
    return {"email": invite.email, "role": invite.role, "company_name": org.name if org else ""}


def accept_invite(db: Session, payload: InviteAccept, days: int) -> tuple[User, str]:
    invite = get_invite(db, payload.token)
    if not payload.name.strip():
        raise HTTPException(422, "Please enter your name.")
    if db.scalar(select(User).where(User.email == invite.email)):
        raise HTTPException(409, "This email address is already registered.")
    claimed = db.execute(
        update(Invite)
        .where(Invite.id == invite.id, Invite.accepted_at.is_(None))
        .values(accepted_at=datetime.now(UTC))
    )
    if claimed.rowcount != 1:  # type: ignore[attr-defined]
        raise HTTPException(409, "This invitation has already been accepted.")
    user = User(
        org_id=invite.org_id,
        name=payload.name.strip(),
        email=invite.email,
        role=invite.role,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "This email address is already registered.") from None
    token = issue_session(db, user, days)
    db.add(
        SecurityAudit(
            org_id=user.org_id, actor_id=user.id, action="invite_accepted", entity_id=invite.id
        )
    )
    db.commit()
    return user, token


def update_member(db: Session, actor: User, member_id: str, payload: TeamUpdate) -> UserResponse:
    require_admin(actor)
    member = db.scalar(select(User).where(User.id == member_id, User.org_id == actor.org_id))
    if member is None:
        raise HTTPException(404)
    if member.id == actor.id or member.role == "Owner":
        raise HTTPException(409, "You cannot change your own role or disable the workspace owner.")
    if payload.role is not None:
        member.role = payload.role
    if payload.is_active is not None:
        member.is_active = payload.is_active
        if not member.is_active:
            db.execute(delete(LoginSession).where(LoginSession.user_id == member.id))
    db.add(
        SecurityAudit(
            org_id=actor.org_id,
            actor_id=actor.id,
            action="team_member_updated",
            entity_id=member.id,
        )
    )
    db.commit()
    return user_response(db, member)


def active_sessions(db: Session, user: User, token: str | None) -> list[dict[str, Any]]:
    token_hash = hashlib.sha256((token or "").encode()).hexdigest()
    sessions = db.scalars(
        select(LoginSession)
        .where(LoginSession.user_id == user.id, LoginSession.expires_at > datetime.now(UTC))
        .order_by(LoginSession.created_at.desc())
    ).all()
    return [
        {
            "id": item.id,
            "created_at": item.created_at.replace(tzinfo=UTC).isoformat(),
            "expires_at": item.expires_at.replace(tzinfo=UTC).isoformat(),
            "current": item.token_hash == token_hash,
        }
        for item in sessions
    ]


def revoke_session_by_id(db: Session, user: User, session_id: str) -> None:
    item = db.scalar(
        select(LoginSession).where(LoginSession.id == session_id, LoginSession.user_id == user.id)
    )
    if item is None:
        raise HTTPException(404)
    db.delete(item)
    db.commit()
