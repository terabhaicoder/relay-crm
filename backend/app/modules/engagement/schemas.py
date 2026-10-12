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
    action_text: str = Field(min_length=1, max_length=500)
    due_days: int = Field(default=1, ge=0, le=365)


class AutomationToggle(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool


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
