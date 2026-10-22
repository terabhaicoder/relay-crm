from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class LineInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    description: str = Field(min_length=1, max_length=500)
    quantity: Decimal = Field(gt=0, le=Decimal("999999.999"), decimal_places=3)
    unit_price: Decimal = Field(ge=0, le=Decimal("999999.9999"), decimal_places=4)


class QuoteFields(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=200)
    valid_until: date | None = None
    terms: str = Field(default="", max_length=10000)
    discount: Decimal = Field(default=Decimal("0.00"), ge=0, decimal_places=2)
    lines: list[LineInput] = Field(min_length=1, max_length=100)


class QuoteCreate(QuoteFields):
    deal_id: str = Field(min_length=1, max_length=36)


class QuoteEdit(QuoteFields):
    version: int = Field(ge=1)


class QuoteTransition(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    version: int = Field(ge=1)
    note: str = Field(default="", max_length=2000)
    close_deal: bool = False
    deal_version: int | None = Field(default=None, ge=1)


class LineResponse(BaseModel):
    id: str
    description: str
    quantity: str
    unit_price: str
    amount: str


class EventResponse(BaseModel):
    action: str
    actor_id: str
    created_at: str
    changes: dict[str, str | bool]


class QuoteResponse(BaseModel):
    id: str
    deal_id: str
    party_id: str | None
    contact_id: str | None
    name: str
    status: Literal["draft", "issued", "accepted", "declined"]
    currency: Literal["INR"]
    customer_name: str
    contact_name: str
    deal_name: str
    valid_until: str | None
    terms: str
    subtotal: str
    discount: str
    total: str
    version: int
    created_at: str
    updated_at: str
    issued_at: str | None
    decided_at: str | None
    decision_note: str
    lines: list[LineResponse]
    events: list[EventResponse]


class QuoteList(BaseModel):
    items: list[QuoteResponse]
    total: int
