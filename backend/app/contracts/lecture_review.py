"""The review queue over the lecture index and the owner's decisions on it: one lecture,
or a whole section or course at once."""

from __future__ import annotations

from pydantic import Field

from app.contracts.common import ApiModel
from app.contracts.comparison import Currency
from app.contracts.lectures import ReviewLectureView


class ReviewQueueView(ApiModel):
    lecture: ReviewLectureView | None
    remaining: int
    reviewed: int
    indexed: int
    # Where the lecture sits: its course's place among the courses still pending (courses
    # for the track's own exam come first), that course's currency, and how many lectures
    # of the course and of its section are still to review.
    course_index: int | None = None
    courses_pending: int = 0
    course_currency: Currency | None = None
    course_pending: int = 0
    section_pending: int = 0


class ReviewDecision(ApiModel):
    course_slug: str = Field(min_length=1, max_length=120)
    lecture_path: str = Field(min_length=1, max_length=1000)
    # Objective codes to pin as this lecture's mappings; empty with exclude=False means
    # "accept as ranked".
    pin: list[str] = Field(default_factory=list)
    exclude: bool = False


class CourseDecision(ApiModel):
    """Accept as ranked, or exclude, every unreviewed lecture of a course, or of one of its
    sections when `section_title` is given."""

    course_slug: str = Field(min_length=1, max_length=120)
    section_title: str | None = Field(default=None, max_length=300)
    exclude: bool = False
