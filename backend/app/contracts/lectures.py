"""The lecture-to-objective index: status, review queue, decisions, and the two lookups."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from app.contracts.common import ApiModel

MappingSource = Literal["rule", "lexical", "pinned", "excluded"]


class LectureMappingView(ApiModel):
    objective_code: str
    objective_title: str
    domain_code: str
    score: float
    normalized: float
    source: MappingSource
    matched_terms: list[str]


class LectureRef(ApiModel):
    course_slug: str
    course_title: str
    exam_code: str | None
    year: int | None
    lecture_path: str
    lecture_title: str
    section_title: str
    duration_seconds: float | None
    word_count: int


class ReviewLectureView(LectureRef):
    excerpt: str
    candidates: list[LectureMappingView]
    reviewed: bool


class ReviewQueueView(ApiModel):
    lecture: ReviewLectureView | None
    remaining: int
    reviewed: int
    indexed: int


class ReviewDecision(ApiModel):
    course_slug: str = Field(min_length=1, max_length=120)
    lecture_path: str = Field(min_length=1, max_length=1000)
    # Objective codes to pin as this lecture's mappings; empty with exclude=False means
    # "accept as ranked".
    pin: list[str] = Field(default_factory=list)
    exclude: bool = False


class IndexStatusView(ApiModel):
    exam_version_id: int
    candidate_courses: int
    lectures_total: int
    lectures_with_captions: int
    lectures_indexed: int
    mappings: int
    reviewed: int
    running: bool
    last_run_at: datetime | None
    last_error: str | None


class ObjectiveLectureView(LectureRef):
    score: float
    normalized: float
    source: MappingSource
    matched_terms: list[str]


class ObjectiveLecturesView(ApiModel):
    objective_code: str
    objective_title: str
    lectures: list[ObjectiveLectureView]
