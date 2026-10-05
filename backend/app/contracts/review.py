"""Flashcard review contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from app.contracts.common import ApiModel, ObjectiveRef

CardSourceKind = Literal["flashcard", "mistake", "note", "custom"]


class CardView(ApiModel):
    id: int
    source_kind: str
    source_item_key: str | None
    source_note_id: int | None
    front_md: str
    back_md: str
    objectives: list[ObjectiveRef]
    state: int
    due: datetime
    due_local: str
    last_review: datetime | None
    suspended: bool
    user_edited: bool
    retrievability: float | None


class DueResponse(ApiModel):
    cards: list[CardView]
    due_total: int
    new_total: int
    reviewed_today: int
    daily_limit: int
    remaining_today: int
    backlog_mode: str
    timezone: str


class RateRequest(ApiModel):
    rating: Literal[1, 2, 3, 4]
    request_id: str = Field(min_length=8, max_length=64)
    duration_ms: int | None = Field(default=None, ge=0, le=3_600_000)


class RateResponse(ApiModel):
    card: CardView
    already_recorded: bool
    reviewed_today: int
    remaining_today: int


class CardCreateRequest(ApiModel):
    source_kind: CardSourceKind = "custom"
    item_key: str | None = None
    note_id: int | None = None
    front_md: str = Field(min_length=1, max_length=4000)
    back_md: str = Field(min_length=1, max_length=8000)


class CardPatch(ApiModel):
    front_md: str | None = Field(default=None, min_length=1, max_length=4000)
    back_md: str | None = Field(default=None, min_length=1, max_length=8000)
    suspended: bool | None = None


class CardListResponse(ApiModel):
    cards: list[CardView]
    total: int
