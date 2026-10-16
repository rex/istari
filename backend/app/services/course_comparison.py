"""Courses compared for a track.

Every candidate course of the active track (the index's rule: the same exam family, or filed
under the track's subject) with what can be measured about it: lectures and captions from
the catalog, the minutes of captioned lecture time mapped to each domain and the objectives
touched from the lecture index, the course's exam against the track's, and what the owner
has watched. Coverage and currency, never a quality score.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import (
    Certification,
    Domain,
    ExamVersion,
    IndexedLecture,
    LectureIndexRun,
    LectureObjective,
    Objective,
)
from app.contracts.comparison import (
    ComparisonDomain,
    CourseComparisonView,
    CourseRow,
    DomainCoverage,
)
from app.domain.watch import Course
from app.services.catalog import CatalogCache
from app.services.course_currency import currency
from app.services.lecture_index import candidate_courses, track_subject
from app.services.watch_progress import completed_counts

Durations = dict[tuple[str, str], float]


@dataclass
class _Tally:
    lectures: set[str] = field(default_factory=set)
    objectives: set[int] = field(default_factory=set)


def _minutes(slug: str, paths: set[str] | list[str], durations: Durations) -> float:
    return round(sum(durations.get((slug, path), 0.0) for path in paths) / 60, 1)


def _row(
    course: Course,
    exam: ExamVersion,
    certification: str,
    durations: Durations,
    domains: list[Domain],
    by_domain: dict[int, _Tally],
    total: _Tally,
    completed: int,
) -> CourseRow:
    lectures = [lecture for section in course.sections for lecture in section.lectures]
    captioned = [lecture.path for lecture in lectures if lecture.caption_path]
    coverage: list[DomainCoverage] = []
    for domain in domains:
        tally = by_domain.get(domain.id, _Tally())
        coverage.append(
            DomainCoverage(
                domain_code=domain.code,
                lectures=len(tally.lectures),
                minutes=_minutes(course.slug, tally.lectures, durations),
                objectives_touched=len(tally.objectives),
            )
        )
    return CourseRow(
        course_slug=course.slug,
        course_title=course.title,
        topic=course.topic,
        exam_code=course.exam_code,
        year=course.year,
        currency=currency(course, exam, certification=certification),
        lectures_total=len(lectures),
        lectures_captioned=len(captioned),
        lectures_mapped=len(total.lectures),
        lectures_completed=completed,
        minutes_captioned=_minutes(course.slug, captioned, durations),
        minutes_mapped=_minutes(course.slug, total.lectures, durations),
        objectives_touched=len(total.objectives),
        domains=coverage,
    )


async def course_comparison(
    db: AsyncSession, catalog: CatalogCache, exam: ExamVersion
) -> CourseComparisonView:
    """One row per candidate course, best coverage first; figures only, the page says the rest."""
    courses = candidate_courses(
        catalog, exam_code=exam.code, subject_slug=await track_subject(db, exam)
    )
    cert = await db.get(Certification, exam.certification_id)
    certification = cert.name if cert else ""
    durations: Durations = {}
    if courses:
        indexed = await db.execute(
            select(
                IndexedLecture.course_slug,
                IndexedLecture.lecture_path,
                IndexedLecture.duration_seconds,
            ).where(IndexedLecture.course_slug.in_([course.slug for course in courses]))
        )
        durations = {
            (str(slug), str(path)): float(seconds or 0.0) for slug, path, seconds in indexed.all()
        }
    domains = list(
        (
            await db.scalars(
                select(Domain).where(Domain.exam_version_id == exam.id).order_by(Domain.position)
            )
        ).all()
    )
    objective_rows = await db.execute(
        select(Objective.id, Objective.domain_id)
        .join(Domain, Domain.id == Objective.domain_id)
        .where(Domain.exam_version_id == exam.id)
    )
    domain_of = {int(objective_id): int(domain_id) for objective_id, domain_id in objective_rows}
    mapped = await db.execute(
        select(
            LectureObjective.course_slug,
            LectureObjective.lecture_path,
            LectureObjective.objective_id,
        ).where(
            LectureObjective.exam_version_id == exam.id,
            LectureObjective.source != "excluded",
        )
    )
    by_course: defaultdict[str, _Tally] = defaultdict(_Tally)
    by_domain: defaultdict[str, defaultdict[int, _Tally]] = defaultdict(lambda: defaultdict(_Tally))
    for slug, path, objective_id in mapped:
        domain_id = domain_of.get(int(objective_id))
        if domain_id is None:
            continue
        for tally in (by_course[str(slug)], by_domain[str(slug)][domain_id]):
            tally.lectures.add(str(path))
            tally.objectives.add(int(objective_id))
    completed = await completed_counts(db)
    last = await db.scalar(
        select(LectureIndexRun)
        .where(LectureIndexRun.exam_version_id == exam.id, LectureIndexRun.status == "done")
        .order_by(LectureIndexRun.id.desc())
        .limit(1)
    )
    rows = [
        _row(
            course,
            exam,
            certification,
            durations,
            domains,
            by_domain[course.slug],
            by_course[course.slug],
            completed.get(course.slug, 0),
        )
        for course in courses
    ]
    rows.sort(
        key=lambda row: (-row.objectives_touched, -row.minutes_mapped, row.course_title.lower())
    )
    return CourseComparisonView(
        exam_version_id=exam.id,
        exam_code=exam.code,
        objectives_total=len(domain_of),
        indexed_at=last.finished_at if last else None,
        scanning=catalog.scanning,
        domains=[
            ComparisonDomain(
                code=domain.code,
                name=domain.name,
                objectives=sum(1 for owner in domain_of.values() if owner == domain.id),
            )
            for domain in domains
        ],
        courses=rows,
    )
