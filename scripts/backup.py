#!/usr/bin/env python3
"""Create/verify/restore CRM snapshots. Stop API writers before backup or restore."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import tempfile


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def connect_readonly(path: Path) -> sqlite3.Connection:
    if path.is_symlink() or not path.is_file():
        raise ValueError("Database must be an existing regular file.")
    return sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)


def check_database(path: Path) -> list[tuple[str, str, int]]:
    with connect_readonly(path) as db:
        if db.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise ValueError("Database integrity check failed.")
        if db.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("Database contains broken foreign keys.")
        tables = {
            row[0]
            for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        if not {"orgs", "users", "attachments", "crm_schema_migrations"}.issubset(
            tables
        ):
            raise ValueError("Database is not a migrated Relay CRM database.")
        return list(
            db.execute("SELECT storage_key, sha256, size_bytes FROM attachments")
        )


def copy_attachment(
    source: Path, destination: Path, key: str, checksum: str, size: int
) -> None:
    if not re.fullmatch(r"[0-9a-f]{32}", key):
        raise ValueError("Invalid attachment storage key.")
    path = source / key
    if path.is_symlink() or not path.is_file():
        raise ValueError("An attachment is missing or is not a regular file.")
    if path.stat().st_size != size or digest(path) != checksum:
        raise ValueError("Attachment checksum mismatch.")
    shutil.copyfile(path, destination / key)
    (destination / key).chmod(0o600)


def backup(database: Path, uploads: Path, output: Path) -> None:
    if output.exists():
        raise ValueError("Backup destination already exists; choose a new directory.")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".relay-backup-", dir=output.parent))
    try:
        snapshot = staging / "relay.db"
        with connect_readonly(database) as source, sqlite3.connect(snapshot) as target:
            source.backup(target)
        snapshot.chmod(0o600)
        attachments = check_database(snapshot)
        (staging / "uploads").mkdir(mode=0o700)
        for key, checksum, size in attachments:
            copy_attachment(uploads, staging / "uploads", key, checksum, size)
        manifest = {
            "format": 1,
            "database_sha256": digest(snapshot),
            "attachments": len(attachments),
        }
        (staging / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        (staging / "manifest.json").chmod(0o600)
        staging.rename(output)
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def verify(source: Path) -> list[tuple[str, str, int]]:
    manifest = json.loads((source / "manifest.json").read_text())
    if manifest.get("format") != 1 or digest(source / "relay.db") != manifest.get(
        "database_sha256"
    ):
        raise ValueError("Backup format or database checksum is invalid.")
    records = check_database(source / "relay.db")
    if manifest.get("attachments") != len(records):
        raise ValueError("Backup attachment count does not match the database.")
    for key, checksum, size in records:
        if not re.fullmatch(r"[0-9a-f]{32}", key):
            raise ValueError("Invalid attachment storage key.")
        path = source / "uploads" / key
        if (
            path.is_symlink()
            or not path.is_file()
            or path.stat().st_size != size
            or digest(path) != checksum
        ):
            raise ValueError("An attachment is missing or its checksum is invalid.")
    return records


def restore(source: Path, output: Path) -> None:
    # Never replace a live database or silently overwrite even an empty directory.
    if output.exists():
        raise ValueError("Restore destination must not exist.")
    records = verify(source)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".relay-restore-", dir=output.parent))
    try:
        shutil.copyfile(source / "relay.db", staging / "relay.db")
        (staging / "relay.db").chmod(0o600)
        (staging / "uploads").mkdir(mode=0o700)
        for key, checksum, size in records:
            copy_attachment(
                source / "uploads", staging / "uploads", key, checksum, size
            )
        check_database(staging / "relay.db")
        staging.rename(output)
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def main() -> None:
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create")
    create.add_argument("--database", type=Path, required=True)
    create.add_argument("--uploads", type=Path, required=True)
    create.add_argument("--output", type=Path, required=True)
    create.add_argument(
        "--writers-stopped",
        action="store_true",
        required=True,
        help="Confirm API processes are stopped to keep files and metadata consistent.",
    )
    check = commands.add_parser("verify")
    check.add_argument("--source", type=Path, required=True)
    recover = commands.add_parser("restore")
    recover.add_argument("--source", type=Path, required=True)
    recover.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "create":
            backup(args.database, args.uploads, args.output)
        elif args.command == "verify":
            verify(args.source)
        else:
            restore(args.source, args.output)
    except (ValueError, OSError, sqlite3.Error, KeyError, TypeError) as error:
        parser.exit(1, f"Snapshot operation failed: {error}\n")
    print(f"Snapshot {args.command} completed successfully.")


if __name__ == "__main__":
    main()
