from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Entity = Literal["leads", "contacts", "parties", "deals", "activities", "campaigns", "tickets"]


class ViewFilters(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    q: str = Field(default="", max_length=200)
    status: str = Field(default="", max_length=30)
    sort: str = Field(default="updated_at:desc", max_length=50)
    pipeline_id: str | None = Field(default=None, max_length=36)
    view: Literal["board", "table"] | None = None


class ViewCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    entity: Entity
    name: str = Field(min_length=1, max_length=80)
    filters: ViewFilters


class ViewUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=80)
    filters: ViewFilters
    version: int = Field(ge=1)


class ViewResponse(BaseModel):
    id: str
    entity: Entity
    name: str
    filters: ViewFilters
    version: int
    created_at: str
    updated_at: str


class ViewList(BaseModel):
    items: list[ViewResponse]
    total: int
