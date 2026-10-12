import re
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# SQLite NUMERIC uses binary storage; this bound preserves cent round-trips.
MAX_MONEY = Decimal("999999999999.99")


class RecordInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(default="", max_length=255)
    owner_id: str | None = None
    tags: list[str] = Field(default_factory=list, max_length=30)
    version: int | None = Field(default=None, ge=1)

    @field_validator(
        "owner_id",
        "party_id",
        "contact_id",
        "deal_id",
        "pipeline_id",
        "stage_id",
        "entity_id",
        "entity_type",
        check_fields=False,
    )
    @classmethod
    def normalize_optional_reference(cls, value: str | None) -> str | None:
        return value or None

    @field_validator(
        "next_follow_up",
        "expected_close_date",
        "due_date",
        "start_date",
        "end_date",
        check_fields=False,
    )
    @classmethod
    def normalize_date(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        if not re.match(r"^\d{4}-\d{2}-\d{2}(?:T|$)", value):
            raise ValueError("Use a YYYY-MM-DD date or an ISO datetime.")
        if len(value) == 10:
            return date.fromisoformat(value).isoformat()
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            raise ValueError("Datetime values need a timezone offset.")
        return timestamp.astimezone(UTC).isoformat()

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, tags: list[str]) -> list[str]:
        if any(len(tag) > 60 for tag in tags):
            raise ValueError("Tags must be 60 characters or shorter.")
        return list(dict.fromkeys(tag.strip() for tag in tags if tag.strip()))


class PersonInput(RecordInput):
    email: str = Field(default="", max_length=255)
    phone: str = Field(default="", max_length=40)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if value and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("Enter a valid email address.")
        return value.lower()

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        if not value:
            return ""
        normalized = re.sub(r"[\s()\-]", "", value)
        if normalized.isdigit() and len(normalized) == 10:
            normalized = "+91" + normalized
        elif normalized.isdigit() and len(normalized) == 12 and normalized.startswith("91"):
            normalized = "+" + normalized
        if not re.fullmatch(r"\+[1-9]\d{7,14}", normalized):
            raise ValueError("Use an international phone number, for example +919876543210.")
        return normalized


class LeadInput(PersonInput):
    company: str = Field(default="", max_length=255)
    title: str = Field(default="", max_length=255)
    source: str = Field(default="Website", max_length=100)
    status: Literal["New", "Contacted", "Qualified", "Unqualified", "Converted"] = "New"
    value: Decimal = Field(
        default=Decimal("0"), ge=0, le=MAX_MONEY, max_digits=18, decimal_places=2
    )
    score: int = Field(default=0, ge=0, le=100)
    next_follow_up: str | None = None
    notes: str = Field(default="", max_length=20000)


class ContactInput(PersonInput):
    company: str = Field(default="", max_length=255)
    party_id: str | None = None
    title: str = Field(default="", max_length=255)
    notes: str = Field(default="", max_length=20000)


class PartyInput(PersonInput):
    website: str = Field(default="", max_length=512)
    industry: str = Field(default="", max_length=120)
    city: str = Field(default="", max_length=120)
    notes: str = Field(default="", max_length=20000)

    @field_validator("website")
    @classmethod
    def validate_website(cls, value: str) -> str:
        if value and not value.startswith(("https://", "http://")):
            raise ValueError("Website must begin with https:// or http://.")
        return value


class DealInput(RecordInput):
    party_id: str | None = None
    contact_id: str | None = None
    pipeline_id: str | None = None
    stage_id: str | None = None
    amount: Decimal = Field(
        default=Decimal("0"), ge=0, le=MAX_MONEY, max_digits=18, decimal_places=2
    )
    probability: int = Field(default=10, ge=0, le=100)
    expected_close_date: str | None = None
    status: Literal["open", "won", "lost"] = "open"
    lost_reason: str = Field(default="", max_length=2000)
    notes: str = Field(default="", max_length=20000)


class ActivityInput(RecordInput):
    type: Literal["task", "call", "meeting", "email", "note", "follow-up"] = "task"
    status: Literal["pending", "completed"] = "pending"
    priority: Literal["low", "medium", "high"] = "medium"
    due_date: str | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    notes: str = Field(default="", max_length=20000)


class CampaignInput(RecordInput):
    type: str = Field(default="email", max_length=30)
    status: Literal["draft", "active", "completed", "paused"] = "draft"
    budget: Decimal = Field(
        default=Decimal("0"), ge=0, le=MAX_MONEY, max_digits=18, decimal_places=2
    )
    spent: Decimal = Field(
        default=Decimal("0"), ge=0, le=MAX_MONEY, max_digits=18, decimal_places=2
    )
    start_date: str | None = None
    end_date: str | None = None
    notes: str = Field(default="", max_length=20000)


class TicketInput(RecordInput):
    deal_id: str | None = None
    priority: Literal["low", "medium", "high", "urgent"] = "medium"
    status: Literal["New", "Open", "Pending", "Resolved", "Closed"] = "New"
    category: str = Field(default="General", max_length=100)
    party_id: str | None = None
    contact_id: str | None = None
    description: str = Field(default="", max_length=20000)


class StageChange(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    stage_id: str = Field(min_length=1, max_length=36)
    version: int | None = Field(default=None, ge=1)
    reason: str = Field(default="", max_length=2000)


class ConvertLead(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    create_deal: bool = True
    deal_name: str | None = None
    amount: Decimal | None = Field(
        default=None, ge=0, le=MAX_MONEY, max_digits=18, decimal_places=2
    )
    contact_id: str | None = None
    party_id: str | None = None


class CSVImport(BaseModel):
    csv: str = Field(max_length=5_000_000)
    mode: Literal["skip", "update", "create"] = "skip"


class MessageInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    body: str = Field(min_length=1, max_length=20000)
    internal: bool = True


class PipelineInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=100)
    stages: list[str] = Field(
        default_factory=lambda: ["Discovery", "Qualified", "Proposal", "Negotiation"],
        min_length=1,
        max_length=12,
    )

    @field_validator("stages")
    @classmethod
    def validate_pipeline_names(cls, names: list[str]) -> list[str]:
        clean = [name.strip() for name in names]
        if any(not name or len(name) > 100 for name in clean):
            raise ValueError("Stage names must contain 1 to 100 characters.")
        folded = [name.casefold() for name in clean]
        if len(set(folded)) != len(folded) or any(name in {"won", "lost"} for name in folded):
            raise ValueError("Use unique open-stage names; Won and Lost are added automatically.")
        return clean


SCHEMAS: dict[str, type[BaseModel]] = {
    "leads": LeadInput,
    "contacts": ContactInput,
    "parties": PartyInput,
    "deals": DealInput,
    "activities": ActivityInput,
    "campaigns": CampaignInput,
    "tickets": TicketInput,
}


class LeadMergeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target_id: str = Field(min_length=1, max_length=36)
    source_version: int | None = Field(default=None, ge=1)
    target_version: int | None = Field(default=None, ge=1)


class LeadMergePair(LeadMergeInput):
    source_id: str = Field(min_length=1, max_length=36)


class CampaignMemberInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    entity_type: Literal["leads", "contacts"]
    entity_id: str = Field(min_length=1, max_length=36)


class PipelineStageInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    id: str | None = None
    name: str = Field(min_length=1, max_length=100)
    probability: int = Field(ge=0, le=100)
    category: Literal["open", "won", "lost"]


class PipelineUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str | None = Field(default=None, min_length=1, max_length=100)
    stages: list[PipelineStageInput] | None = Field(default=None, min_length=3, max_length=14)
