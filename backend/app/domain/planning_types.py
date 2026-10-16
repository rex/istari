"""Inputs and outputs of the next-session planner (`recommendation.py`). Pure data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

BlockKind = Literal["resume", "review", "practice", "lab", "lesson", "lecture"]
# Whether verified labs can be scheduled: no backend configured, configured but silent, or ready.
LabBackend = Literal["unconfigured", "unreachable", "ready"]


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
class LabCandidate:
    """A verified lab the planner may schedule, with the objective it serves."""

    item_key: str
    title: str
    estimated_minutes: int
    objective_code: str
    objective_title: str


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
    verified_lab: LabCandidate | None = None
    lab_backend: LabBackend = "unconfigured"
    next_lecture: LectureCandidate | None = None


@dataclass(frozen=True, slots=True)
class LectureCandidate:
    """The next unwatched lecture on the weakest objective's learning path."""

    course_slug: str
    lecture_path: str
    title: str
    course_title: str
    objective_code: str
    minutes: int


@dataclass(frozen=True, slots=True)
class PlanBlock:
    kind: BlockKind
    count: int
    label: str
    reason: str
    focus: str | None = None
    session_id: int | None = None
    item_key: str | None = None
    course_slug: str | None = None
    lecture_path: str | None = None


@dataclass(frozen=True, slots=True)
class Plan:
    minutes: int
    headline: str
    blocks: tuple[PlanBlock, ...]
    explanation: tuple[str, ...]
    weakest: tuple[ObjectiveEvidence, ...]
