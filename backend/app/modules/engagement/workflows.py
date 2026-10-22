"""Durable local workflows: CRM effects and their execution receipt commit together."""

import asyncio
import logging
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.db import ensure_write_transaction
from app.modules.auth.models import User, utcnow
from app.modules.crm.repository import MODELS, CRMRepository
from app.modules.crm.service import serialize
from app.modules.engagement.models import Automation, AutomationJob, AutomationRun, Notification

MANAGERS = {"Owner", "Admin", "Sales Manager"}
JOB_STATUSES = {"queued", "completed", "failed", "cancelled", "skipped"}
logger = logging.getLogger(__name__)


def require_manager(user: User) -> None:
    if not user.is_active or user.role not in MANAGERS:
        raise HTTPException(403, "Only an active workspace or sales manager can manage workflows.")


def validate_targets(db: Session, user: User, steps: list[dict[str, Any]]) -> None:
    for step in steps:
        if step.get("owner_id"):
            target_user(db, user.org_id, step["owner_id"])


def target_user(db: Session, org_id: str, user_id: str) -> User:
    target = db.scalar(
        select(User).where(User.org_id == org_id, User.id == user_id, User.is_active.is_(True))
    )
    if target is None:
        raise HTTPException(404, "The selected teammate is unavailable in this workspace.")
    return target


@contextmanager
def suppress_automation(db: Session) -> Iterator[None]:
    previous = db.info.get("automation_dispatch_depth", 0)
    db.info["automation_dispatch_depth"] = previous + 1
    try:
        yield
    finally:
        db.info["automation_dispatch_depth"] = previous


def enqueue(db: Session, rule: Automation, entity_type: str, record: Any, event_key: str) -> None:
    """Snapshot the whole chain inside the originating CRM transaction."""
    created = utcnow()
    run = AutomationRun(
        org_id=rule.org_id,
        rule_id=rule.id,
        event_key=event_key,
        entity_type=entity_type,
        entity_id=record.id,
        entity_name=record.name[:255],
        rule_name=rule.name,
        status="queued",
        result="Workflow queued",
    )
    db.add(run)
    db.flush()
    legacy = not rule.steps
    steps = rule.steps or [
        {
            "action": rule.action,
            "action_text": rule.action_text,
            "due_days": rule.due_days,
            "delay_minutes": 0,
            "owner_id": None,
        }
    ]
    first: AutomationJob | None = None
    for index, step in enumerate(steps, start=1):
        job = AutomationJob(
            org_id=rule.org_id,
            run_id=run.id,
            rule_id=rule.id,
            actor_id=rule.owner_id,
            rule_name=rule.name,
            entity_type=entity_type,
            entity_id=record.id,
            entity_name=record.name[:255],
            step_index=index,
            action=step["action"],
            snapshot={
                "step": deepcopy(step),
                "conditions": deepcopy(rule.conditions),
                "trigger": rule.trigger,
                "legacy": legacy,
            },
            scheduled_at=created + timedelta(minutes=step.get("delay_minutes", 0))
            if index == 1
            else None,
            status="queued",
        )
        db.add(job)
        if index == 1:
            first = job
    db.flush()
    if legacy and first is not None:
        execute_job(db, first, created)


def refresh_run(db: Session, job: AutomationJob, at: datetime) -> None:
    db.flush()
    run = db.scalar(
        select(AutomationRun).where(
            AutomationRun.org_id == job.org_id,
            AutomationRun.id == job.run_id,
        )
    )
    assert run is not None
    jobs = list(
        db.scalars(
            select(AutomationJob)
            .where(
                AutomationJob.org_id == job.org_id,
                AutomationJob.run_id == job.run_id,
            )
            .order_by(AutomationJob.step_index)
        )
    )
    statuses = {item.status for item in jobs}
    if "failed" in statuses:
        run.status, run.result = (
            "failed",
            "A workflow step failed; review its error before retrying.",
        )
    elif "queued" in statuses:
        run.status, run.result = "queued", "Waiting for scheduled steps"
    elif "cancelled" in statuses:
        run.status, run.result = "cancelled", "Remaining workflow steps were cancelled"
    elif "skipped" in statuses:
        run.status, run.result = "skipped", "Conditions no longer matched"
    else:
        run.status = "completed"
        run.result = jobs[-1].result if len(jobs) == 1 else f"Completed {len(jobs)} workflow steps"
    run.completed_at = None if run.status in {"queued", "failed"} else at


def cancel_remaining(
    db: Session, job: AutomationJob, reason: str, at: datetime, *, status: str = "cancelled"
) -> None:
    for pending in db.scalars(
        select(AutomationJob).where(
            AutomationJob.org_id == job.org_id,
            AutomationJob.run_id == job.run_id,
            AutomationJob.status.in_(["queued", "failed"]),
        )
    ):
        pending.status, pending.result, pending.completed_at = status, reason, at
    refresh_run(db, job, at)


def perform_action(db: Session, job: AutomationJob, actor: User, record: Any, at: datetime) -> None:
    from app.modules.crm import service as crm_service

    step = job.snapshot["step"]
    recipient = target_user(db, job.org_id, step.get("owner_id") or record.owner_id or actor.id)
    title = str(step.get("action_text", "")).replace("{{name}}", record.name)
    with suppress_automation(db):
        if job.action == "create_task":
            linked_type = record.entity_type if job.entity_type == "activities" else job.entity_type
            linked_id = record.entity_id if job.entity_type == "activities" else record.id
            task = crm_service.create(
                db,
                actor,
                "activities",
                {
                    "name": title[:255],
                    "owner_id": recipient.id,
                    "type": "task",
                    "status": "pending",
                    "priority": "medium",
                    "due_date": (
                        at.astimezone(ZoneInfo("Asia/Kolkata")).date()
                        + timedelta(days=step.get("due_days", 1))
                    ).isoformat(),
                    "entity_type": linked_type,
                    "entity_id": linked_id,
                    "notes": f"Created by automation: {job.rule_name}",
                },
            )
            job.result, job.result_entity_type, job.result_entity_id = (
                "Follow-up task created",
                "activities",
                task.id,
            )
            db.add(
                Notification(
                    org_id=job.org_id,
                    user_id=recipient.id,
                    title=title[:500],
                    entity_type=job.entity_type,
                    entity_id=job.entity_id,
                )
            )
        elif job.action == "notify":
            notification = Notification(
                org_id=job.org_id,
                user_id=recipient.id,
                title=title[:500],
                entity_type=job.entity_type,
                entity_id=job.entity_id,
            )
            db.add(notification)
            db.flush()
            job.result, job.result_entity_type, job.result_entity_id = (
                "Notification created",
                job.entity_type,
                job.entity_id,
            )
        elif job.action == "assign_owner":
            crm_service.modify(
                db,
                actor,
                job.entity_type,
                job.entity_id,
                {"owner_id": recipient.id, "version": record.version},
            )
            job.result = "Record assigned to the selected teammate"
            job.result_entity_type, job.result_entity_id = job.entity_type, job.entity_id
        else:
            raise HTTPException(422, "This workflow action is unsupported.")


def execute_job(db: Session, job: AutomationJob, at: datetime) -> None:
    """No running state commits separately: crashes roll back both effects and receipt."""
    from app.modules.engagement.service import matches

    if job.status != "queued":
        return
    rule = db.scalar(
        select(Automation).where(Automation.id == job.rule_id, Automation.org_id == job.org_id)
    )
    if rule is None or not rule.enabled:
        cancel_remaining(db, job, "Rule was paused; pending steps cancelled", at)
        return
    job.started_at, job.attempts = at, job.attempts + 1
    try:
        # Flush attempt metadata before the savepoint; action failures can then be recorded.
        with db.begin_nested():
            actor = target_user(db, job.org_id, job.actor_id)
            require_manager(actor)
            record = CRMRepository(db, actor).get(job.entity_type, job.entity_id)
            if not matches(job.snapshot["conditions"], record):
                cancel_remaining(
                    db, job, "Conditions no longer match the current record", at, status="skipped"
                )
                return
            perform_action(db, job, actor, record, at)
            db.flush()
    except HTTPException as error:
        job.status, job.error_detail = "failed", str(error.detail)[:2000]
        job.result = "Step failed; no partial action was saved"
        job.completed_at = at
        refresh_run(db, job, at)
        return
    except Exception:
        job.status, job.error_detail = (
            "failed",
            "The action could not be completed. Check the record and teammate, then retry.",
        )
        job.result = "Step failed; no partial action was saved"
        job.completed_at = at
        refresh_run(db, job, at)
        return
    job.status, job.completed_at, job.error_detail = "completed", at, ""
    next_job = db.scalar(
        select(AutomationJob).where(
            AutomationJob.org_id == job.org_id,
            AutomationJob.run_id == job.run_id,
            AutomationJob.step_index == job.step_index + 1,
            AutomationJob.status == "queued",
        )
    )
    if next_job:
        next_job.scheduled_at = at + timedelta(
            minutes=next_job.snapshot["step"].get("delay_minutes", 0)
        )
    refresh_run(db, job, at)


def process_due_jobs(
    session_factory: Callable[[], Session], *, limit: int = 50, at: datetime | None = None
) -> dict[str, int]:
    """Process a bounded batch; safe under overlapping local workers and process restarts."""
    result = {"processed": 0, "completed": 0, "failed": 0, "skipped": 0, "cancelled": 0}
    for _ in range(min(max(limit, 0), 200)):
        with session_factory() as db:
            ensure_write_transaction(db)
            cutoff = at or utcnow()
            job = db.scalar(
                select(AutomationJob)
                .where(
                    AutomationJob.status == "queued",
                    AutomationJob.scheduled_at.is_not(None),
                    AutomationJob.scheduled_at <= cutoff,
                )
                .order_by(AutomationJob.scheduled_at, AutomationJob.id)
                .limit(1)
            )
            if job is None:
                db.rollback()
                break
            execute_job(db, job, cutoff)
            result["processed"] += 1
            result[job.status] += 1
            db.commit()
    return result


async def worker_loop(
    session_factory: Callable[[], Session], stop: asyncio.Event, *, interval_seconds: float = 2.0
) -> None:
    """Root lifespan owns this local worker's start/stop; no external queue required."""
    while not stop.is_set():
        try:
            await asyncio.to_thread(process_due_jobs, session_factory)
        except Exception:
            # A temporary database failure must not silently stop the local worker.
            # The transaction remains queued after rollback; avoid logging record data.
            logger.error("workflow_worker_failed", extra={"safe_event": "workflow_worker_failed"})
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval_seconds)
        except TimeoutError:
            continue


def visible_query(db: Session, user: User, model: Any) -> Any:
    query = select(model).where(model.org_id == user.org_id)
    if user.role in {"Sales Rep", "Sales Representative"}:
        repo = CRMRepository(db, user)
        query = query.where(
            or_(
                *[
                    (model.entity_type == entity)
                    & select(record.id)
                    .where(
                        record.id == model.entity_id,
                        *repo.scope(record),
                    )
                    .exists()
                    for entity in MODELS
                    for record in [repo.model(entity)]
                ]
            )
        )
    return query


def encode_job(job: AutomationJob) -> dict[str, Any]:
    result = serialize(job)
    result.pop("snapshot", None)
    result["trigger"] = job.snapshot.get("trigger", "")
    result["delay_minutes"] = job.snapshot["step"].get("delay_minutes", 0)
    return result


def history(
    db: Session,
    user: User,
    *,
    jobs: bool,
    q: str = "",
    rule_id: str | None = None,
    status: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    model: Any = AutomationJob if jobs else AutomationRun
    query = visible_query(db, user, model)
    if status:
        if status not in JOB_STATUSES:
            raise HTTPException(422, "Choose a supported execution status.")
        query = query.where(model.status == status)
    if rule_id:
        rule = db.scalar(
            select(Automation).where(Automation.org_id == user.org_id, Automation.id == rule_id)
        )
        if rule is None:
            raise HTTPException(404, "Automation not found.")
        query = query.where(model.rule_id == rule_id)
    if entity_type:
        if entity_type not in MODELS:
            raise HTTPException(422, "Choose a supported CRM record type.")
        query = query.where(model.entity_type == entity_type)
    if entity_id:
        if not entity_type:
            raise HTTPException(422, "Choose the related record type with its ID.")
        CRMRepository(db, user).get(entity_type, entity_id)
        query = query.where(model.entity_id == entity_id)
    if q:
        escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        columns = [model.rule_name, model.entity_name, model.result]
        if jobs:
            columns.append(model.error_detail)
        query = query.where(or_(*(column.ilike(f"%{escaped}%", escape="\\") for column in columns)))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(query.order_by(model.created_at.desc(), model.id).offset(offset).limit(limit))
    return {
        "items": [encode_job(row) if jobs else serialize(row) for row in rows],
        "total": total,
        "page": offset // limit + 1,
        "page_size": limit,
    }


def pause_pending(db: Session, rule: Automation) -> None:
    at = utcnow()
    pending = list(
        db.scalars(
            select(AutomationJob).where(
                AutomationJob.org_id == rule.org_id,
                AutomationJob.rule_id == rule.id,
                AutomationJob.status.in_(["queued", "failed"]),
            )
        )
    )
    for job in pending:
        job.status, job.result, job.completed_at = (
            "cancelled",
            "Rule was paused; pending steps cancelled",
            at,
        )
    for job in {job.run_id: job for job in pending}.values():
        refresh_run(db, job, at)


def manage_job(db: Session, user: User, job_id: str, action: str) -> dict[str, Any]:
    require_manager(user)
    ensure_write_transaction(db)
    job = db.scalar(
        select(AutomationJob).where(AutomationJob.org_id == user.org_id, AutomationJob.id == job_id)
    )
    if job is None:
        raise HTTPException(404, "Workflow step not found.")
    if action == "cancel":
        if job.status not in {"queued", "failed"}:
            raise HTTPException(409, "Only queued or failed steps can be cancelled.")
        cancel_remaining(db, job, "Cancelled by a workspace manager", utcnow())
    else:
        CRMRepository(db, user).get(job.entity_type, job.entity_id)
        if job.status != "failed" or job.attempts >= 10:
            raise HTTPException(
                409, "Only a failed step with fewer than ten attempts can be retried."
            )
        rule = db.scalar(
            select(Automation).where(Automation.org_id == user.org_id, Automation.id == job.rule_id)
        )
        if rule is None or not rule.enabled:
            raise HTTPException(409, "The rule must be active before a failed step can be retried.")
        require_manager(target_user(db, job.org_id, job.actor_id))
        job.status, job.scheduled_at, job.completed_at = "queued", utcnow(), None
        job.error_detail, job.result = "", "Retry queued by a workspace manager"
        refresh_run(db, job, utcnow())
    db.commit()
    return encode_job(job)
