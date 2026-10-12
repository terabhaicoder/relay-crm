"""Local operator recovery: python -m app.reset_password --email owner@example.com.

The operator needs access to the private database/container. No email delivery is
claimed. Passwords are read privately and every existing session is revoked.
"""

import argparse
import getpass
import os
import sys

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.bootstrap import initialize_database
from app.core.config import Settings, get_settings
from app.core.db import build_local_engine, ensure_write_transaction
from app.modules.auth.models import LoginSession, SecurityAudit, User
from app.modules.auth.service import hash_password


def reset_password(settings: Settings, email: str, password: str) -> None:
    if not 8 <= len(password) <= 128:
        raise ValueError("Use a password between 8 and 128 characters.")
    engine = build_local_engine(settings)
    try:
        initialize_database(engine, settings)
        with Session(engine) as session:
            ensure_write_transaction(session)
            user = session.scalar(select(User).where(User.email == email.strip().lower()))
            if user is None:
                raise ValueError("Account not found.")
            user.password_hash = hash_password(password)
            session.execute(delete(LoginSession).where(LoginSession.user_id == user.id))
            # actor_id is the affected account context, not an authenticated caller.
            # The distinct action records the actual local operating-system operator.
            session.add(
                SecurityAudit(
                    org_id=user.org_id,
                    actor_id=user.id,
                    action=f"operator_password_reset_uid_{os.getuid()}",
                    entity_id=user.id,
                )
            )
            session.commit()
    finally:
        engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True)
    parser.add_argument("--password-stdin", action="store_true")
    args = parser.parse_args()
    if args.password_stdin:
        password = sys.stdin.readline().rstrip("\r\n")
    else:
        password = getpass.getpass("New password: ")
        if password != getpass.getpass("Confirm password: "):
            parser.error("Passwords do not match.")
    try:
        reset_password(get_settings(), args.email, password)
    except ValueError:
        parser.exit(1, "Password reset failed. Check the account and password requirements.\n")
    print("Password reset completed; all existing sessions have been revoked.")


if __name__ == "__main__":
    main()
