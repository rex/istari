"""The Watch area: courses on the learning share, their lectures, and playback progress."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.contracts.common import ApiModel


class CatalogStatus(ApiModel):
    configured: bool
    root: str | None
    topics: list[str]
    scanned_at: datetime | None
    scanning: bool
    course_count: int


class LectureProgressView(ApiModel):
    position_seconds: float
    duration_seconds: float | None
    completed_at: datetime | None
    last_watched_at: datetime | None


class CourseSummary(ApiModel):
    slug: str
    title: str
    topic: str
    exam_code: str | None
    year: int | None
    lecture_count: int
    caption_count: int
    completed_count: int
    # Most recently watched lecture, for a "continue" link.
    resume_path: str | None
    resume_title: str | None


class CoursesView(ApiModel):
    status: CatalogStatus
    courses: list[CourseSummary]


class LectureView(ApiModel):
    path: str
    title: str
    has_captions: bool
    size_bytes: int
    progress: LectureProgressView | None


class SectionView(ApiModel):
    title: str
    lectures: list[LectureView]


class CourseView(ApiModel):
    slug: str
    title: str
    topic: str
    exam_code: str | None
    year: int | None
    lecture_count: int
    completed_count: int
    sections: list[SectionView]


class ProgressUpdate(ApiModel):
    lecture_path: str = Field(min_length=1, max_length=1000)
    position_seconds: float = Field(ge=0)
    duration_seconds: float | None = Field(default=None, gt=0)
    completed: bool = False
