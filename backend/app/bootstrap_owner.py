"""Create the first workspace owner without enabling public signup.

Run: python -m app.bootstrap_owner --name "Owner" --email owner@example.com
     --company "Company". Passwords are prompted privately, never command arguments.
"""

import argparse
import getpass
import sys

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.bootstrap import initialize_database
from app.core.config import Settings, get_settings
from app.core.db import build_local_engine, ensure_write_transaction
from app.modules.auth.models import User
from app.modules.auth.schemas import SignupRequest
from app.modules.auth.service import create_account


def bootstrap_owner(settings: Settings, payload: SignupRequest) -> str:
    engine = build_local_engine(settings)
    try:
        initialize_database(engine, settings)
        with Session(engine) as session:
            ensure_write_transaction(session)
            if session.scalar(select(func.count()).select_from(User)):
                raise ValueError("An account already exists. Sign in to manage your workspace.")
            user = create_account(session, payload)
            session.commit()
            return user.id
    finally:
        engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--company", required=True)
    parser.add_argument(
        "--password-stdin",
        action="store_true",
        help="Read the password from stdin for controlled automation.",
    )
    args = parser.parse_args()
    if args.password_stdin:
        password = sys.stdin.readline().rstrip("\r\n")
    else:
        password = getpass.getpass("New owner password: ")
        if password != getpass.getpass("Confirm password: "):
            parser.error("Passwords do not match.")
    try:
        payload = SignupRequest(
            name=args.name, email=args.email, company_name=args.company, password=password
        )
        bootstrap_owner(get_settings(), payload)
    except ValueError:
        parser.exit(
            1,
            "Owner creation failed. Use an empty database, valid account details "
            "and a password of at least 8 characters.\n",
        )
    print("Workspace owner created. Sign in with your chosen email and password.")


if __name__ == "__main__":
    main()
