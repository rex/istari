"""Course currency: the exam code, the certification's name and the year in a course title."""

from __future__ import annotations

from datetime import date

import pytest

from app.adapters.db.models import ExamVersion
from app.contracts.comparison import Currency
from app.domain.watch import Course
from app.services.course_currency import currency

SAA = "AWS Certified Solutions Architect - Associate"


def _exam(current_since: date | None = date(2022, 8, 30)) -> ExamVersion:
    return ExamVersion(code="SAA-C03", name="SAA-C03", current_since=current_since)


def _course(title: str, *, code: str | None = None, year: int | None = None) -> Course:
    return Course(
        slug="c", title=title, topic="Cloud/AWS", exam_code=code, year=year, root="/x", sections=()
    )


@pytest.mark.parametrize(
    ("title", "year", "expected"),
    [
        ("AWS Certified Solutions Architect - Associate 2018", 2018, "older"),
        ("Ultimate AWS Certified Solutions Architect Associate 2024", 2024, "current"),
        # The year the version changed could be either side of the change.
        ("Ultimate AWS Certified Solutions Architect Associate 2022", 2022, "same_exam"),
        ("AWS Certified Solutions Architect Associate", None, "same_exam"),
    ],
)
def test_a_year_reads_against_the_date_the_version_became_current(
    title: str, year: int | None, expected: Currency
) -> None:
    assert currency(_course(title, year=year), _exam(), certification=SAA) == expected


def test_without_a_date_in_the_pack_the_year_says_nothing() -> None:
    course = _course("AWS Certified Solutions Architect - Associate 2018", year=2018)
    assert currency(course, _exam(current_since=None), certification=SAA) == "same_exam"


def test_a_code_in_the_title_outranks_the_year() -> None:
    dated = _course("Solutions Architect Associate 2024 [SAA-C02]", code="SAA-C02", year=2024)
    assert currency(dated, _exam(), certification=SAA) == "older"
    named = _course("SAA-C03 Solutions Architect Associate 2018", year=2018)
    assert currency(named, _exam(), certification=SAA) == "current"


def test_other_exams_ignore_the_year() -> None:
    professional = _course("AWS Certified Solutions Architect - Professional 2018", year=2018)
    assert currency(professional, _exam(), certification=SAA) == "other"
    unrelated = _course("Docker Mastery 2018", year=2018)
    assert currency(unrelated, _exam(), certification=SAA) == "unknown"
