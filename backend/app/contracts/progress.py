"""Honest progress views. No readiness percentage; evidence is labelled."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from app.contracts.common import ApiModel, ObjectiveRef
from app.contracts.today import PlanBlockView

EvidenceLevel = Literal["insufficient", "weak", "developing", "solid"]


class ObjectiveProgress(ApiModel):
    code: str
    title: str
    domain_code: str
    lessons_total: int
    lessons_completed: int
    questions_total: int
    families_seen: int
    first_attempts: int
    first_correct: int
    first_accuracy: float | None
    repeat_attempts: int
    repeat_correct: int
    repeat_accuracy: float | None
    assessment_attempts: int
    assessment_correct: int
    evidence: EvidenceLevel
    self_declared_familiar: bool
    # Verified labs serving this objective: how many exist, how many were graded at least
    # once, and how many passed on their first graded attempt (the only pass that counts).
    labs_total: int = 0
    labs_attempted: int = 0
    labs_passed_first: int = 0


class DomainProgress(ApiModel):
    code: str
    name: str
    weight_percent: int
    objectives: list[ObjectiveProgress]
    first_attempts: int
    first_correct: int
    first_accuracy: float | None
    lessons_total: int
    lessons_completed: int
    labs_total: int = 0
    labs_passed_first: int = 0


class ConfidentMistakeView(ApiModel):
    item_key: str
    stem_md: str
    objectives: list[ObjectiveRef]
    answered_at: datetime
    session_id: int
    has_card: bool


class ActivityDay(ApiModel):
    date: date
    answers: int
    reviews: int
    lessons: int


class ProgressTotals(ApiModel):
    first_attempts: int
    first_correct: int
    first_accuracy: float | None
    repeat_attempts: int
    repeat_correct: int
    repeat_accuracy: float | None
    assessment_attempts: int
    assessment_correct: int
    assessment_sessions: int
    lessons_total: int
    lessons_completed: int
    cards_total: int
    cards_due: int
    questions_total: int
    families_seen: int
    labs_total: int = 0
    labs_attempted: int = 0
    labs_passed_first: int = 0


class ProgressFlags(ApiModel):
    invalidated_items: int
    excluded_answers: int
    note: str


class ProgressView(ApiModel):
    totals: ProgressTotals
    domains: list[DomainProgress]
    weak_areas: list[ObjectiveProgress]
    confident_mistakes: list[ConfidentMistakeView]
    recent_activity: list[ActivityDay]
    flags: ProgressFlags
    next_action: PlanBlockView | None
    evidence_note: str
