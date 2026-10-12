import os
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse
from sqlalchemy.exc import IntegrityError

from app.core.auth import CurrentUser, SessionDep, require_write
from app.modules.crm.service import idempotent_result, record_event, remember
from app.modules.files import service
from app.modules.files.models import Attachment

router = APIRouter(tags=["Attachments"])


@router.get("/attachments")
def attachments(
    db: SessionDep, user: CurrentUser, entity_type: str, entity_id: str
) -> dict[str, Any]:
    return {"items": service.list_attachments(db, user, entity_type, entity_id)}


@router.post("/attachments", status_code=201)
async def upload_attachment(
    request: Request,
    db: SessionDep,
    user: CurrentUser,
    entity_type: str,
    entity_id: str,
    filename: str = Query(min_length=1, max_length=200),
    idempotency_key: str | None = Header(default=None),
) -> dict[str, Any]:
    require_write(user)
    parent = service.parent_record(db, user, entity_type, entity_id)
    filename = service.validate_filename(filename)
    directory = request.app.state.settings.upload_dir.resolve()
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    key = uuid4().hex
    path = service.storage_path(directory, key)
    size = 0
    committed = False
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as output:
            async for chunk in request.stream():
                size += len(chunk)
                if size > service.MAX_FILE_BYTES:
                    raise HTTPException(413, "Files must be 10 MB or smaller.")
                output.write(chunk)
        content_type, digest = service.validate_content(
            path, filename, request.headers.get("content-type", "")
        )
        route = f"{user.id}/attachments"
        payload = {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "filename": filename,
            "content_type": content_type,
            "sha256": digest,
            "size_bytes": size,
        }
        previous, payload_digest = idempotent_result(db, user, idempotency_key, route, payload)
        if previous:
            return service.encode(service.get_attachment(db, user, previous["id"]))
        record = Attachment(
            org_id=user.org_id,
            owner_id=user.id,
            entity_type=entity_type,
            entity_id=entity_id,
            filename=filename,
            storage_key=key,
            content_type=content_type,
            size_bytes=size,
            sha256=digest,
        )
        db.add(record)
        db.flush()
        record_event(db, user, entity_type, parent, "attachment_added", {"filename": filename})
        result = service.encode(record)
        remember(db, user, idempotency_key, route, payload_digest, result)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            # A simultaneous retry may have committed while this request wrote
            # its staged file. Revalidate current access before replaying it.
            previous, _ = idempotent_result(db, user, idempotency_key, route, payload)
            if previous:
                return service.encode(service.get_attachment(db, user, previous["id"]))
            raise HTTPException(409, "Attachment changed. Refresh and retry.") from None
        committed = True
        return result
    finally:
        if not committed:
            db.rollback()
            path.unlink(missing_ok=True)


@router.get("/attachments/{attachment_id}/download")
def download_attachment(
    attachment_id: str, request: Request, db: SessionDep, user: CurrentUser
) -> FileResponse:
    record = service.get_attachment(db, user, attachment_id)
    path = service.storage_path(request.app.state.settings.upload_dir.resolve(), record.storage_key)
    if not path.is_file():
        raise HTTPException(404)
    return FileResponse(
        path,
        media_type=record.content_type,
        filename=record.filename,
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.delete("/attachments/{attachment_id}", status_code=204)
def delete_attachment(
    attachment_id: str, request: Request, db: SessionDep, user: CurrentUser
) -> Response:
    require_write(user)
    record = service.get_attachment(db, user, attachment_id)
    parent = service.parent_record(db, user, record.entity_type, record.entity_id)
    directory = request.app.state.settings.upload_dir.resolve()
    path = service.storage_path(directory, record.storage_key)
    tombstone = directory / (record.storage_key + ".deleting")
    moved = False
    try:
        if path.exists():
            path.replace(tombstone)
            moved = True
        record_event(
            db,
            user,
            record.entity_type,
            parent,
            "attachment_deleted",
            {"filename": record.filename},
        )
        db.delete(record)
        db.commit()
    except Exception:
        db.rollback()
        if moved:
            tombstone.replace(path)
        raise
    if moved:
        tombstone.unlink(missing_ok=True)
    return Response(status_code=204)
