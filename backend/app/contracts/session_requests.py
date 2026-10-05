"""Request/response bodies for the session endpoints (views live in `session.py`)."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.contracts.common import ApiModel
from app.contracts.session import Confidence, SessionItemView, SessionKind


class SessionCreateRequest(ApiModel):
    kind: SessionKind = "practice"
    minutes: Literal[5, 15, 30] = 15
    # mixed | weak | objective:<code>
    focus: str = Field(default="mixed", max_length=64)
    replace_active: bool = False


class DraftRequest(ApiModel):
    selected_option_ids: list[str] = Field(max_length=6)
    confidence: Confidence | None = None
    expected_version: int = Field(ge=1)


class AnswerRequest(ApiModel):
    selected_option_ids: list[str] = Field(min_length=1, max_length=6)
    confidence: Confidence | None = None
    # Client-generated UUID; a retried request with the same id is a no-op.
    request_id: str = Field(min_length=8, max_length=64)


class AnswerResponse(ApiModel):
    item: SessionItemView
    session_version: int
    already_recorded: bool
    answered_count: int
    total: int
    status: Literal["in_progress", "completed", "abandoned"]
