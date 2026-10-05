"""Study session contracts. Answer keys appear only inside `FeedbackView`."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from app.contracts.common import ApiModel, ObjectiveRef, SourceView

SessionKind = Literal["practice", "assessment"]
Confidence = Literal["guessing", "uncertain", "confident"]


class OptionView(ApiModel):
    id: str
    text_md: str


class AnswerView(ApiModel):
    selected_option_ids: list[str]
    # None while feedback is withheld (assessment before completion).
    is_correct: bool | None
    confidence: Confidence | None
    first_attempt: bool
    answered_at: datetime


class FeedbackView(ApiModel):
    correct_option_ids: list[str]
    explanation_md: str
    distractor_rationales: dict[str, str]
    decisive_constraint: str
    objectives: list[ObjectiveRef]
    sources: list[SourceView]
    missed_option_ids: list[str]
    extra_option_ids: list[str]


class SessionItemView(ApiModel):
    position: int
    item_key: str
    family_key: str
    stem_md: str
    select_count: int
    difficulty: str
    objectives: list[ObjectiveRef]
    options: list[OptionView]
    state: Literal["pending", "answered"]
    draft_selection: list[str] | None
    draft_confidence: Confidence | None
    answer: AnswerView | None
    feedback: FeedbackView | None


class SessionView(ApiModel):
    id: int
    kind: SessionKind
    focus: str
    planned_minutes: int
    status: Literal["in_progress", "completed", "abandoned"]
    version: int
    created_at: datetime
    completed_at: datetime | None
    answered_count: int
    correct_count: int | None
    total: int
    feedback_visible: bool
    explanation: dict[str, object]
    items: list[SessionItemView]


class ActiveSessionView(ApiModel):
    id: int
    kind: SessionKind
    answered_count: int
    total: int
    planned_minutes: int
    created_at: datetime
