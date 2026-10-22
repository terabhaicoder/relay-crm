from decimal import Decimal, InvalidOperation
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Condition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field: Literal["status", "source", "priority", "score", "amount", "value", "company"]
    operator: Literal["equals", "contains", "gte"] = "equals"
    value: str = Field(max_length=300)

    @model_validator(mode="after")
    def validate_comparison(self) -> Self:
        if self.operator == "gte":
            if self.field not in {"score", "amount", "value"}:
                raise ValueError("At least is available only for numeric fields.")
            try:
                valid = Decimal(self.value).is_finite()
            except InvalidOperation:
                valid = False
            if not valid:
                raise ValueError("Enter a finite number for an At least condition.")
        return self


class AutomationStep(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    action: Literal["create_task", "notify", "assign_owner"]
    delay_minutes: int = Field(default=0, ge=0, le=43200)
    action_text: str = Field(default="", max_length=500)
    due_days: int = Field(default=1, ge=0, le=365)
    owner_id: str | None = Field(default=None, max_length=36)

    @model_validator(mode="after")
    def validate_step(self) -> Self:
        if self.action in {"create_task", "notify"} and not self.action_text:
            raise ValueError("Task and notification steps need their text.")
        if self.action == "assign_owner" and not self.owner_id:
            raise ValueError("Choose a teammate for assignment.")
        return self


class AutomationInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=200)
    trigger: Literal[
        "leads.created",
        "leads.updated",
        "leads.converted",
        "deals.created",
        "deals.won",
        "deals.lost",
        "deals.stage_changed",
        "tickets.created",
        "tickets.updated",
        "activities.created",
        "activities.completed",
    ]
    enabled: bool = True
    conditions: list[Condition] = Field(default_factory=list, max_length=10)
    action: Literal["create_task", "notify"] = "create_task"
    action_text: str = Field(default="Follow up {{name}}", min_length=1, max_length=500)
    due_days: int = Field(default=1, ge=0, le=365)
    steps: list[AutomationStep] = Field(default_factory=list, max_length=8)

    @model_validator(mode="after")
    def validate_delays(self) -> Self:
        if sum(step.delay_minutes for step in self.steps) > 43200:
            raise ValueError("The combined step delays cannot exceed 30 days.")
        if self.trigger == "leads.converted" and any(
            step.action == "assign_owner" for step in self.steps
        ):
            raise ValueError(
                "Converted leads are read-only; use a task or notification after conversion."
            )
        return self


class AutomationToggle(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool


ExecutionStatus = Literal["queued", "completed", "failed", "cancelled", "skipped"]


class AutomationJobResponse(BaseModel):
    id: str
    created_at: str
    run_id: str
    rule_id: str
    actor_id: str
    rule_name: str
    entity_type: str
    entity_id: str
    entity_name: str
    step_index: int
    action: Literal["create_task", "notify", "assign_owner"]
    trigger: str
    delay_minutes: int
    status: ExecutionStatus
    scheduled_at: str | None
    started_at: str | None
    completed_at: str | None
    attempts: int
    result: str
    result_entity_type: str | None
    result_entity_id: str | None
    error_detail: str


class AutomationRunResponse(BaseModel):
    id: str
    created_at: str
    rule_id: str
    event_key: str
    entity_type: str
    entity_id: str
    entity_name: str
    rule_name: str
    status: ExecutionStatus
    result: str
    completed_at: str | None


class AutomationJobList(BaseModel):
    items: list[AutomationJobResponse]
    total: int
    page: int
    page_size: int


class AutomationRunList(BaseModel):
    items: list[AutomationRunResponse]
    total: int
    page: int
    page_size: int


class TemplateInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=200)
    subject: str = Field(min_length=1, max_length=300)
    body: str = Field(min_length=1, max_length=20000)


class DraftInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    recipient: str = Field(min_length=3, max_length=254)
    subject: str = Field(min_length=1, max_length=300)
    body: str = Field(min_length=1, max_length=20000)
    entity_type: str | None = None
    entity_id: str | None = None

    @field_validator("recipient")
    @classmethod
    def validate_recipient(cls, value: str) -> str:
        import re

        if not re.fullmatch(r"[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+", value):
            raise ValueError("Enter one valid email address.")
        return value.lower()
