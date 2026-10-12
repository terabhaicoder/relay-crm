from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


def now() -> datetime:
    return datetime.now(UTC)


class Record:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("orgs.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    owner_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True, index=True
    )
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now, onupdate=now, index=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)


class Lead(Record, Base):
    __tablename__ = "leads"
    email: Mapped[str] = mapped_column(String(255), default="", index=True)
    phone: Mapped[str] = mapped_column(String(40), default="", index=True)
    company: Mapped[str] = mapped_column(String(255), default="")
    title: Mapped[str] = mapped_column(String(255), default="")
    source: Mapped[str] = mapped_column(String(100), default="Website")
    status: Mapped[str] = mapped_column(String(30), default="New", index=True)
    value: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    score: Mapped[int] = mapped_column(Integer, default=0)
    next_follow_up: Mapped[str | None] = mapped_column(String(40), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    converted_contact_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    converted_party_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    converted_deal_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    __table_args__ = (Index("ix_leads_org_owner_status", "org_id", "owner_id", "status"),)


class Contact(Record, Base):
    __tablename__ = "contacts"
    email: Mapped[str] = mapped_column(String(255), default="", index=True)
    phone: Mapped[str] = mapped_column(String(40), default="", index=True)
    company: Mapped[str] = mapped_column(String(255), default="")
    party_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("parties.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), default="")
    notes: Mapped[str] = mapped_column(Text, default="")


class Party(Record, Base):
    __tablename__ = "parties"
    email: Mapped[str] = mapped_column(String(255), default="")
    phone: Mapped[str] = mapped_column(String(40), default="")
    website: Mapped[str] = mapped_column(String(512), default="")
    industry: Mapped[str] = mapped_column(String(120), default="")
    city: Mapped[str] = mapped_column(String(120), default="")
    notes: Mapped[str] = mapped_column(Text, default="")


class Pipeline(Record, Base):
    __tablename__ = "pipelines"


class Stage(Base):
    __tablename__ = "stages"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("orgs.id"), index=True)
    pipeline_id: Mapped[str] = mapped_column(String(36), ForeignKey("pipelines.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    probability: Mapped[int] = mapped_column(Integer, default=0)
    position: Mapped[int] = mapped_column(Integer)
    category: Mapped[str] = mapped_column(String(20), default="open")
    color: Mapped[str] = mapped_column(String(20), default="#64748b")


class Deal(Record, Base):
    __tablename__ = "deals"
    party_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("parties.id"), nullable=True
    )
    contact_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("contacts.id"), nullable=True
    )
    pipeline_id: Mapped[str] = mapped_column(String(36), ForeignKey("pipelines.id"))
    stage_id: Mapped[str] = mapped_column(String(36), ForeignKey("stages.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    probability: Mapped[int] = mapped_column(Integer, default=10)
    expected_close_date: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)
    lost_reason: Mapped[str] = mapped_column(Text, default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    stage_entered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (Index("ix_deals_org_status_stage", "org_id", "status", "stage_id"),)


class Activity(Record, Base):
    __tablename__ = "activities"
    type: Mapped[str] = mapped_column(String(30), default="task")
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    priority: Mapped[str] = mapped_column(String(20), default="medium")
    due_date: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    entity_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Campaign(Record, Base):
    __tablename__ = "campaigns"
    type: Mapped[str] = mapped_column(String(30), default="email")
    status: Mapped[str] = mapped_column(String(30), default="draft")
    budget: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    spent: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    start_date: Mapped[str | None] = mapped_column(String(40), nullable=True)
    end_date: Mapped[str | None] = mapped_column(String(40), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")


class Ticket(Record, Base):
    __tablename__ = "tickets"
    deal_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("deals.id"), nullable=True)
    priority: Mapped[str] = mapped_column(String(20), default="medium")
    status: Mapped[str] = mapped_column(String(30), default="New", index=True)
    category: Mapped[str] = mapped_column(String(100), default="General")
    party_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("parties.id"), nullable=True
    )
    contact_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("contacts.id"), nullable=True
    )
    description: Mapped[str] = mapped_column(Text, default="")
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TicketMessage(Base):
    __tablename__ = "ticket_messages"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("orgs.id"), index=True)
    ticket_id: Mapped[str] = mapped_column(String(36), ForeignKey("tickets.id"), index=True)
    author_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text)
    internal: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class StageHistory(Base):
    __tablename__ = "deal_stage_history"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    org_id: Mapped[str] = mapped_column(String(36), index=True)
    deal_id: Mapped[str] = mapped_column(String(36), ForeignKey("deals.id"), index=True)
    from_stage_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    to_stage_id: Mapped[str] = mapped_column(String(36))
    actor_id: Mapped[str] = mapped_column(String(36))
    reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    org_id: Mapped[str] = mapped_column(String(36), index=True)
    actor_id: Mapped[str] = mapped_column(String(36))
    entity_type: Mapped[str] = mapped_column(String(30))
    entity_id: Mapped[str] = mapped_column(String(36), index=True)
    action: Mapped[str] = mapped_column(String(40))
    changes: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict[str, Any])
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class IdempotencyRecord(Base):
    __tablename__ = "crm_idempotency_keys"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    org_id: Mapped[str] = mapped_column(String(36), index=True)
    key: Mapped[str] = mapped_column(String(255))
    route: Mapped[str] = mapped_column(String(255))
    payload_hash: Mapped[str] = mapped_column(String(64))
    response: Mapped[dict[str, Any]] = mapped_column(JSON)
    __table_args__ = (UniqueConstraint("org_id", "route", "key"),)


class CampaignMember(Base):
    __tablename__ = "campaign_members"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("orgs.id"), index=True)
    campaign_id: Mapped[str] = mapped_column(String(36), ForeignKey("campaigns.id"), index=True)
    entity_type: Mapped[str] = mapped_column(String(30))
    entity_id: Mapped[str] = mapped_column(String(36))
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (UniqueConstraint("org_id", "campaign_id", "entity_type", "entity_id"),)
