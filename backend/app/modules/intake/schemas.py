from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.crm.schemas import PersonInput


class FormInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=2000)
    source: str = Field(default="Website", min_length=1, max_length=100)
    enabled: bool = True
    owner_ids: list[str] = Field(default_factory=list, max_length=50)
    version: int | None = Field(default=None, ge=1)


class FormResponse(FormInput):
    id: str
    version: int
    submissions: int
    new_leads: int
    duplicates: int
    created_at: datetime


class FormList(BaseModel):
    items: list[FormResponse]
    total: int


class PublicForm(BaseModel):
    id: str
    title: str
    description: str
    organization: str


class SubmissionInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=255)
    email: str = Field(min_length=3, max_length=255)
    phone: str = Field(default="", max_length=40)
    company: str = Field(default="", max_length=255)
    message: str = Field(default="", max_length=4000)
    consent: Literal[True]

    def person(self) -> PersonInput:
        return PersonInput(name=self.name, email=self.email, phone=self.phone)


class Receipt(BaseModel):
    accepted: Literal[True] = True
    message: str = "Thank you. Your inquiry has been received."


class SubmissionResponse(BaseModel):
    id: str
    lead_id: str
    name: str
    message: str
    duplicate: bool
    created_at: datetime


class SubmissionList(BaseModel):
    items: list[SubmissionResponse]
    total: int
