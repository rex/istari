"""Learning paths: one per objective, composed across courses, edited by the owner."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from app.contracts.common import ApiModel

PathSource = Literal["pinned", "proposed"]
LectureKey = tuple[str, str]


class PathEntryView(ApiModel):
    position: int
    course_slug: str
    course_title: str
    lecture_path: str
    lecture_title: str
    section_title: str
    minutes: float | None
    reason: str
    source: PathSource
    completed: bool


class ExcludedEntryView(ApiModel):
    course_slug: str
    course_title: str
    lecture_path: str
    lecture_title: str


class ObjectivePathView(ApiModel):
    objective_code: str
    objective_title: str
    domain_code: str
    entries: list[PathEntryView]
    excluded: list[ExcludedEntryView]
    # Older-exam courses that stepped aside because a current one covers the same ground.
    stale_courses: list[str]
    total_minutes: float
    courses: list[str]
    composed_at: datetime | None
    # The first entry not yet watched: where "continue" starts.
    resume_position: int | None


class PathSummaryView(ApiModel):
    objective_code: str
    objective_title: str
    domain_code: str
    entries: int
    completed: int
    total_minutes: float


class PathsView(ApiModel):
    exam_version_id: int
    composed_at: datetime | None
    objectives: list[PathSummaryView]


class PathDecision(ApiModel):
    # The whole order the owner wants, as (course_slug, lecture_path): every key becomes a pin.
    order: list[LectureKey] = Field(default_factory=list)
    exclude: list[LectureKey] = Field(default_factory=list)
    restore: list[LectureKey] = Field(default_factory=list)
    # Forget every pin and exclusion for the objective and compose afresh.
    reset: bool = False
