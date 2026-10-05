"""Shared pieces of the pack schema: keys, sources, provenance, review status."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

KEY_PATTERN = r"^[a-z0-9][a-z0-9-]{1,98}$"
OBJECTIVE_CODE_PATTERN = r"^\d+\.\d+$"
DOMAIN_CODE_PATTERN = r"^\d+$"

Key = Annotated[str, StringConstraints(pattern=KEY_PATTERN)]
ObjectiveCode = Annotated[str, StringConstraints(pattern=OBJECTIVE_CODE_PATTERN)]
DomainCode = Annotated[str, StringConstraints(pattern=DOMAIN_CODE_PATTERN)]
NonEmpty = Annotated[str, StringConstraints(min_length=1, strip_whitespace=True)]

ReviewStatus = Literal["draft", "source_checked", "human_reviewed"]
AuthoredBy = Literal["ai", "human"]
Difficulty = Literal["easy", "medium", "hard"]


class StrictModel(BaseModel):
    """Unknown keys are schema errors — a typo must never silently drop content."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SourceRef(StrictModel):
    title: NonEmpty
    url: NonEmpty
    checked_on: date

    @field_validator("url")
    @classmethod
    def url_must_be_http(cls, value: str) -> str:
        if not value.startswith(("https://", "http://")):
            raise ValueError("source url must start with http:// or https://")
        return value


class Provenance(StrictModel):
    authored_by: AuthoredBy
    # Model or person name, e.g. "Claude Fable 5.1" or "pierce".
    author: NonEmpty
    authored_on: date
    # True when every technical claim was checked against the listed sources.
    # This is NOT human review; `review_status` carries that separately.
    source_checked: bool = False
    notes: str = ""


class ItemBase(StrictModel):
    """Fields every content item carries regardless of kind."""

    # The item's permanent identifier within its pack. Named `slug`, not `key`, because
    # secret scanners read `"key": "<value>"` as a credential.
    slug: Key
    objectives: list[ObjectiveCode] = Field(min_length=1)
    sources: list[SourceRef] = Field(min_length=1)
    provenance: Provenance
    review_status: ReviewStatus = "draft"
    tags: list[str] = Field(default_factory=list)

    @field_validator("objectives")
    @classmethod
    def objectives_unique(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value):
            raise ValueError("objective codes must be unique")
        return value
