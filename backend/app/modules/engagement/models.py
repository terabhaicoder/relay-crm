from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.modules.auth.models import new_id, utcnow


class ScopedRecord:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    org_id: Mapped[str] = mapped_column(ForeignKey("orgs.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Automation(ScopedRecord, Base):
    __tablename__ = "automation_rules"
    name: Mapped[str] = mapped_column(String(200))
    trigger: Mapped[str] = mapped_column(String(80))
    enabled: Mapped[bool] = mapped_column(default=True)
    conditions: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    action: Mapped[str] = mapped_column(String(40), default="create_task")
    action_text: Mapped[str] = mapped_column(String(500))
    due_days: Mapped[int] = mapped_column(default=1)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    steps: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)


class AutomationRun(ScopedRecord, Base):
    __tablename__ = "automation_runs"
    rule_id: Mapped[str] = mapped_column(ForeignKey("automation_rules.id"), index=True)
    event_key: Mapped[str] = mapped_column(String(200))
    entity_type: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[str] = mapped_column(String(36))
    status: Mapped[str] = mapped_column(String(30), default="completed")
    result: Mapped[str] = mapped_column(String(500), default="")
    rule_name: Mapped[str] = mapped_column(String(200), default="")
    entity_name: Mapped[str] = mapped_column(String(255), default="")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (UniqueConstraint("org_id", "rule_id", "event_key"),)


class AutomationJob(ScopedRecord, Base):
    __tablename__ = "automation_jobs"
    run_id: Mapped[str] = mapped_column(ForeignKey("automation_runs.id"), index=True)
    rule_id: Mapped[str] = mapped_column(ForeignKey("automation_rules.id"), index=True)
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    rule_name: Mapped[str] = mapped_column(String(200))
    entity_type: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[str] = mapped_column(String(36))
    entity_name: Mapped[str] = mapped_column(String(255))
    step_index: Mapped[int] = mapped_column()
    action: Mapped[str] = mapped_column(String(40))
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(30), default="queued", index=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempts: Mapped[int] = mapped_column(default=0)
    result: Mapped[str] = mapped_column(String(500), default="")
    result_entity_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    result_entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    error_detail: Mapped[str] = mapped_column(Text, default="")
    __table_args__ = (UniqueConstraint("org_id", "run_id", "step_index"),)


class Notification(ScopedRecord, Base):
    __tablename__ = "notifications"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(500))
    entity_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    read: Mapped[bool] = mapped_column(default=False)


class EmailTemplate(ScopedRecord, Base):
    __tablename__ = "email_templates"
    name: Mapped[str] = mapped_column(String(200))
    subject: Mapped[str] = mapped_column(String(300))
    body: Mapped[str] = mapped_column(Text)


class EmailDraft(ScopedRecord, Base):
    __tablename__ = "email_messages"
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    recipient: Mapped[str] = mapped_column(String(254))
    subject: Mapped[str] = mapped_column(String(300))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="draft")
    entity_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
