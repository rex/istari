"""The review queue: the next lecture the owner has not looked at, with the courses for the
track's own exam first, and decisions on a whole section or course at once."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import (
    Certification,
    ExamVersion,
    IndexedLecture,
    LectureObjective,
    LectureReview,
)
from app.contracts.lecture_review import CourseDecision, ReviewQueueView
from app.domain.learning_path import CURRENCY_RANK
from app.domain.naming import natural_key
from app.services.catalog import CatalogCache
from app.services.course_currency import currency
from app.services.lecture_index import MACHINE_SOURCES
from app.services.lecture_mapping import lecture_view

LectureKey = tuple[str, str]
# (course_slug, lecture_path, section_title)
Pending = tuple[str, str, str]


async def _pending(db: AsyncSession, exam_version_id: int) -> list[Pending]:
    """Lectures with machine mappings for the track that the owner has not decided on."""
    reviewed = select(LectureReview.course_slug, LectureReview.lecture_path).where(
        LectureReview.exam_version_id == exam_version_id
    )
    rows = await db.execute(
        select(
            LectureObjective.course_slug,
            LectureObjective.lecture_path,
            IndexedLecture.section_title,
        )
        .join(
            IndexedLecture,
            (IndexedLecture.course_slug == LectureObjective.course_slug)
            & (IndexedLecture.lecture_path == LectureObjective.lecture_path),
        )
        .where(
            LectureObjective.exam_version_id == exam_version_id,
            LectureObjective.source.in_(MACHINE_SOURCES),
        )
        .distinct()
    )
    done = {(slug, path) for slug, path in (await db.execute(reviewed)).all()}
    return [
        (str(slug), str(path), str(section))
        for slug, path, section in rows.all()
        if (slug, path) not in done
    ]


async def _currencies(
    db: AsyncSession, exam: ExamVersion, catalog: CatalogCache, slugs: set[str]
) -> dict[str, str]:
    cert = await db.get(Certification, exam.certification_id)
    name = cert.name if cert else ""
    out: dict[str, str] = {}
    for slug in slugs:
        course = catalog.by_slug(slug)
        out[slug] = currency(course, exam, certification=name) if course else "unknown"
    return out


def _ordered(pending: list[Pending], currencies: dict[str, str]) -> list[Pending]:
    """Courses for the track's own exam first, then by course and lecture order."""
    return sorted(
        pending,
        key=lambda item: (CURRENCY_RANK.get(currencies[item[0]], 5), item[0], natural_key(item[1])),
    )


async def review_queue(
    db: AsyncSession, exam: ExamVersion, catalog: CatalogCache, *, after: LectureKey | None = None
) -> ReviewQueueView:
    """The next lecture to decide on, past `after` when it is still pending."""
    pending = await _pending(db, exam.id)
    currencies = await _currencies(db, exam, catalog, {slug for slug, _, _ in pending})
    ordered = _ordered(pending, currencies)
    reviewed = await db.scalar(
        select(func.count(LectureReview.id)).where(LectureReview.exam_version_id == exam.id)
    )
    indexed = await db.scalar(select(func.count(IndexedLecture.id)))
    keys = [(slug, path) for slug, path, _ in ordered]
    start = keys.index(after) + 1 if after in keys else 0
    if start >= len(ordered):
        start = 0
    if not ordered:
        return ReviewQueueView(
            lecture=None, remaining=0, reviewed=int(reviewed or 0), indexed=int(indexed or 0)
        )
    slug, path, section = ordered[start]
    courses: list[str] = []
    for other, _, _ in ordered:
        if other not in courses:
            courses.append(other)
    return ReviewQueueView(
        lecture=await lecture_view(db, exam.id, (slug, path), reviewed=False),
        remaining=len(ordered),
        reviewed=int(reviewed or 0),
        indexed=int(indexed or 0),
        course_index=courses.index(slug) + 1,
        courses_pending=len(courses),
        course_currency=currencies[slug],  # type: ignore[arg-type]
        course_pending=sum(1 for other, _, _ in ordered if other == slug),
        section_pending=sum(1 for other, _, sec in ordered if other == slug and sec == section),
    )


async def decide_course(
    db: AsyncSession, exam: ExamVersion, decision: CourseDecision, *, now: datetime
) -> int:
    """Accept as ranked, or exclude, every unreviewed lecture of a course or of one section;
    one review row per lecture, so the per-lecture lookups and the index stay as they are."""
    chosen = [
        item
        for item in await _pending(db, exam.id)
        if item[0] == decision.course_slug
        and (decision.section_title is None or item[2] == decision.section_title)
    ]
    if not chosen:
        return 0
    if decision.exclude:
        rows = await db.scalars(
            select(LectureObjective).where(
                LectureObjective.exam_version_id == exam.id,
                LectureObjective.course_slug == decision.course_slug,
                LectureObjective.lecture_path.in_([path for _, path, _ in chosen]),
            )
        )
        for row in rows.all():
            row.source = "excluded"
    label = "excluded" if decision.exclude else "accepted"
    for slug, path, _ in chosen:
        db.add(
            LectureReview(
                exam_version_id=exam.id,
                course_slug=slug,
                lecture_path=path,
                decision=label,
                reviewed_at=now,
            )
        )
    await db.flush()
    return len(chosen)
