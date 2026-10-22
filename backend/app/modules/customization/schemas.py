from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictStr, model_validator

CustomEntity = Literal["leads", "contacts", "parties", "deals", "tickets"]
CustomType = Literal["text", "number", "date", "boolean", "select"]
CustomValue = StrictStr | StrictBool | None


class CustomDefinitionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    entity: CustomEntity
    field_key: str = Field(pattern=r"^[a-z][a-z0-9_]{0,39}$")
    label: str = Field(min_length=1, max_length=100)
    field_type: CustomType
    description: str = Field(default="", max_length=300)
    options: list[str] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def valid_options(self) -> Self:
        validate_options(self.field_type, self.options)
        return self


def validate_options(field_type: str, options: list[str]) -> None:
    if field_type == "select":
        if not options or any(not item or len(item) > 80 for item in options):
            raise ValueError("Select fields need 1–50 nonempty choices of up to 80 characters.")
        if len(options) != len(set(options)):
            raise ValueError("Select choices must be unique.")
    elif options:
        raise ValueError("Only select fields can have choices.")


class CustomDefinitionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    version: int = Field(ge=1)
    label: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=300)
    options: list[str] | None = Field(default=None, max_length=50)
    archived: bool | None = None


class CustomValuesUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int = Field(ge=0)
    values: dict[str, CustomValue] = Field(min_length=1, max_length=100)


class CustomDefinitionResponse(BaseModel):
    id: str
    entity: CustomEntity
    field_key: str
    label: str
    field_type: CustomType
    description: str
    options: list[str]
    archived: bool
    version: int


class CustomDefinitionList(BaseModel):
    items: list[CustomDefinitionResponse]
    total: int


class CustomFieldChange(BaseModel):
    field_id: str
    label: str
    before: CustomValue
    after: CustomValue


class CustomFieldEvent(BaseModel):
    action: str
    actor_id: str
    created_at: str
    changes: list[CustomFieldChange]


class CustomRecordResponse(BaseModel):
    entity: CustomEntity
    record_id: str
    version: int
    fields: list[CustomDefinitionResponse]
    values: dict[str, CustomValue]
    history: list[CustomFieldEvent]
