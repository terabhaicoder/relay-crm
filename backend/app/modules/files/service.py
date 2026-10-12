import hashlib
from datetime import UTC
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.modules.auth.models import User
from app.modules.crm.repository import CRMRepository
from app.modules.files.models import Attachment

MAX_FILE_BYTES = 10 * 1024 * 1024
MIME_TYPES = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".txt": "text/plain",
    ".csv": "text/csv",
}
ENTITIES = {"leads", "contacts", "parties", "deals", "activities", "campaigns", "tickets"}


def parent_record(db: Session, user: User, entity_type: str, entity_id: str) -> Any:
    if entity_type not in ENTITIES:
        raise HTTPException(422, "Choose a supported record for this attachment.")
    return CRMRepository(db, user).get(entity_type, entity_id)


def validate_filename(filename: str) -> str:
    filename = filename.strip()
    if (
        not filename
        or len(filename) > 200
        or "/" in filename
        or "\\" in filename
        or any(ord(character) < 32 or ord(character) == 127 for character in filename)
    ):
        raise HTTPException(
            422, "Choose a simple filename without folders or special control characters."
        )
    if Path(filename).suffix.lower() not in MIME_TYPES:
        raise HTTPException(422, "Upload a PDF, PNG, JPG, TXT or CSV file.")
    return filename


def validate_content(path: Path, filename: str, declared_type: str) -> tuple[str, str]:
    data = path.read_bytes()
    if not data:
        raise HTTPException(422, "The selected file is empty.")
    extension = Path(filename).suffix.lower()
    expected = MIME_TYPES[extension]
    allowed = {expected, "application/octet-stream", ""}
    if extension == ".csv":
        allowed |= {"text/plain", "application/vnd.ms-excel"}
    if declared_type.split(";", 1)[0].strip().lower() not in allowed:
        raise HTTPException(422, "The file type does not match its filename.")
    valid = True
    if extension == ".pdf":
        valid = data.startswith(b"%PDF-") and b"%%EOF" in data[-1024:]
    elif extension == ".png":
        valid = data.startswith(b"\x89PNG\r\n\x1a\n") and b"IEND" in data[-32:]
    elif extension in {".jpg", ".jpeg"}:
        valid = data.startswith(b"\xff\xd8\xff") and data.endswith(b"\xff\xd9")
    else:
        try:
            content = data.decode("utf-8-sig")
            valid = not any(
                ord(character) < 32 and character not in "\r\n\t" for character in content
            )
        except UnicodeDecodeError:
            valid = False
    if not valid:
        raise HTTPException(422, "The file contents do not match the selected file type.")
    return expected, hashlib.sha256(data).hexdigest()


def encode(attachment: Attachment) -> dict[str, Any]:
    created_at = attachment.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    return {
        "id": attachment.id,
        "filename": attachment.filename,
        "content_type": attachment.content_type,
        "size_bytes": attachment.size_bytes,
        "created_at": created_at.isoformat(),
        "owner_id": attachment.owner_id,
        "entity_type": attachment.entity_type,
        "entity_id": attachment.entity_id,
    }


def list_attachments(
    db: Session, user: User, entity_type: str, entity_id: str
) -> list[dict[str, Any]]:
    parent_record(db, user, entity_type, entity_id)
    records = db.scalars(
        select(Attachment)
        .where(
            Attachment.org_id == user.org_id,
            Attachment.entity_type == entity_type,
            Attachment.entity_id == entity_id,
        )
        .order_by(Attachment.created_at.desc())
        .limit(100)
    ).all()
    return [encode(record) for record in records]


def get_attachment(db: Session, user: User, attachment_id: str) -> Attachment:
    record = db.scalar(
        select(Attachment).where(Attachment.id == attachment_id, Attachment.org_id == user.org_id)
    )
    if record is None:
        raise HTTPException(404)
    parent_record(db, user, record.entity_type, record.entity_id)
    return record


def storage_path(directory: Path, key: str) -> Path:
    if len(key) != 32 or any(character not in "0123456789abcdef" for character in key):
        raise HTTPException(500, "Attachment storage is unavailable.")
    return directory / key


def relink_entity(
    db: Session, user: User, entity_type: str, source_id: str, target_id: str
) -> None:
    """Move a record's attachments within the caller's merge transaction."""
    parent_record(db, user, entity_type, source_id)
    parent_record(db, user, entity_type, target_id)
    db.execute(
        update(Attachment)
        .where(
            Attachment.org_id == user.org_id,
            Attachment.entity_type == entity_type,
            Attachment.entity_id == source_id,
        )
        .values(entity_id=target_id)
    )
