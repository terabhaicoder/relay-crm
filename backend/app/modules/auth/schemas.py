import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not re.fullmatch(r"[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+", value):
            raise ValueError("Enter a valid email address.")
        return value


class SignupRequest(LoginRequest):
    name: str = Field(min_length=1, max_length=200)
    company_name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("name", "company_name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field is required.")
        return value


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    org_id: str
    name: str
    email: str
    role: str
    company_name: str
    is_active: bool = True


class TeamCreate(LoginRequest):
    name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=8, max_length=128)
    role: Literal["Admin", "Sales Manager", "Sales Rep", "Support Agent", "Read-only"] = "Sales Rep"


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class ProfileUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class InviteCreate(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    role: Literal["Admin", "Sales Manager", "Sales Rep", "Support Agent", "Read-only"] = "Sales Rep"

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return LoginRequest.normalize_email(value)


class InviteAccept(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=8, max_length=128)


class TeamUpdate(BaseModel):
    role: Literal["Admin", "Sales Manager", "Sales Rep", "Support Agent", "Read-only"] | None = None
    is_active: bool | None = None
