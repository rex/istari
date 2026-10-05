"""Inputs and outputs of the next-session planner (`recommendation.py`). Pure data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

BlockKind = Literal["resume", "review", "practice", "lesson"]


@dataclass(frozen=True, slots=True)
class ObjectiveEvidence:
    code: str
    title: str
    domain_weight: int
    first_attempts: int
    first_correct: int
    available_questions: int

    @property
    def accuracy(self) -> float | None:
        if self.first_attempts == 0:
            return None
        return self.first_correct / self.first_attempts


@dataclass(frozen=True, slots=True)
class ActiveSession:
    session_id: int
    kind: str
    answered: int
    total: int


@dataclass(frozen=True, slots=True)
class LessonCandidate:
    item_key: str
    title: str
    estimated_minutes: int


@dataclass(frozen=True, slots=True)
class PlannerInput:
    minutes: int
    active_session: ActiveSession | None
    due_reviews: int
    reviews_remaining_today: int
    backlog_mode: str
    objectives: tuple[ObjectiveEvidence, ...]
    available_questions: int
    next_lesson: LessonCandidate | None


@dataclass(frozen=True, slots=True)
class PlanBlock:
    kind: BlockKind
    count: int
    label: str
    reason: str
    focus: str | None = None
    session_id: int | None = None
    item_key: str | None = None


@dataclass(frozen=True, slots=True)
class Plan:
    minutes: int
    headline: str
    blocks: tuple[PlanBlock, ...]
    explanation: tuple[str, ...]
    weakest: tuple[ObjectiveEvidence, ...]
