"""Base classes and shared response shapes."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")


class ErrorBody(ApiModel):
    """Every non-2xx response has this shape."""

    error: str
    message: str
    details: dict[str, object] = Field(default_factory=dict)
    request_id: str = "-"


class OkResponse(ApiModel):
    ok: Literal[True] = True


class SourceView(ApiModel):
    title: str
    url: str
    checked_on: str


class ObjectiveRef(ApiModel):
    code: str
    title: str
    domain_code: str
