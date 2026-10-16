"""Courses compared for a track: coverage per domain, depth, currency, captions, progress."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from app.contracts.common import ApiModel

# How a course's exam relates to the track's: the same version, an older or newer version of
# the same exam, the same certification with no version named, another exam, or no exam
# named in its folder.
Currency = Literal["current", "older", "newer", "same_exam", "other", "unknown"]


class DomainCoverage(ApiModel):
    domain_code: str
    lectures: int
    minutes: float
    objectives_touched: int


class CourseRow(ApiModel):
    course_slug: str
    course_title: str
    topic: str
    exam_code: str | None
    year: int | None
    currency: Currency
    lectures_total: int
    lectures_captioned: int
    lectures_mapped: int
    lectures_completed: int
    # Minutes come from captions, so a lecture without them adds nothing to either figure.
    minutes_captioned: float
    minutes_mapped: float
    objectives_touched: int
    domains: list[DomainCoverage]


class ComparisonDomain(ApiModel):
    code: str
    name: str
    objectives: int


class CourseComparisonView(ApiModel):
    exam_version_id: int
    exam_code: str
    objectives_total: int
    indexed_at: datetime | None
    # True while the catalog scan runs: the rows are what the last scan found, or nothing.
    scanning: bool
    domains: list[ComparisonDomain]
    courses: list[CourseRow]
