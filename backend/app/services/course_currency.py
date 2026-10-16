"""How a course on the share relates to a track's exam: the same version, an older or newer
one, the same certification with no version named, another exam, or none named."""

from __future__ import annotations

import re
from datetime import date

from app.adapters.db.models import ExamVersion
from app.contracts.comparison import Currency
from app.domain.naming import names_certification, names_other_level
from app.domain.watch import Course

_NUMBERS = re.compile(r"\d+")


def exam_family(code: str | None) -> str | None:
    """ "SAA" for "SAA-C03": the part of an exam code that survives a version bump."""
    return code.split("-")[0].upper() if code else None


def own_exam(course: Course, exam: ExamVersion) -> bool:
    """Whether a course is for this track's exam: its family, or the exact code in its title
    (the catalog only parses the codes it knows)."""
    family = exam_family(exam.code)
    return family is not None and (
        exam_family(course.exam_code) == family or exam.code.lower() in course.title.lower()
    )


def version_key(code: str) -> tuple[int, ...]:
    """ "SAA-C03" -> (3,), "CKA-1.35" -> (1, 35): the part of a code that a version bump moves."""
    return tuple(int(part) for part in _NUMBERS.findall(code.partition("-")[2]))


def currency(course: Course, exam: ExamVersion, *, certification: str) -> Currency:
    """A course without a parsed code still counts as current when the track's exact code is
    in its title, and as the same exam when the certification's name is; then the year in
    its name, read against the date this exam version replaced the previous one, says
    whether it is for an older version (dated before) or this one (dated after)."""
    if course.exam_code is None:
        if own_exam(course, exam):
            return "current"
        if names_certification(course.title, certification):
            return _dated(course.year, exam.current_since)
        return "other" if names_other_level(course.title, certification) else "unknown"
    if exam_family(course.exam_code) != exam_family(exam.code):
        return "other"
    theirs, mine = version_key(course.exam_code), version_key(exam.code)
    if theirs == mine:
        return "current"
    return "older" if theirs < mine else "newer"


def _dated(year: int | None, current_since: date | None) -> Currency:
    """Version unknown unless the course's year and the exam's date are both known and
    differ: the year the version changed could be either side of it."""
    if year is None or current_since is None or year == current_since.year:
        return "same_exam"
    return "older" if year < current_since.year else "current"
