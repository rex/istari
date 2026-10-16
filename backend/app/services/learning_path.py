"""Learning paths: one per objective, composed from the lecture index and kept as a proposal
the owner edits. Every index run recomposes the `proposed` rows; `pinned` and `excluded`
rows are the owner's and stay. Lengths come from captions, so an unmeasured lecture shows
no minutes and costs a fallback against the cap."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import (
    Certification,
    CourseProgress,
    Domain,
    ExamVersion,
    IndexedLecture,
    LectureObjective,
    Objective,
    ObjectivePathEntry,
)
from app.contracts.paths import (
    ExcludedEntryView,
    ObjectivePathView,
    PathDecision,
    PathEntryView,
    PathSummaryView,
    PathsView,
)
from app.domain.exceptions import NotFoundError
from app.domain.learning_path import PathLecture, compose_path, stale_courses
from app.domain.planning_types import LectureCandidate, ObjectiveEvidence
from app.domain.recommendation import weakest_objectives
from app.services.catalog import CatalogCache
from app.services.course_currency import currency

Key = tuple[str, str]


async def _objectives(db: AsyncSession, exam: ExamVersion) -> list[tuple[Objective, Domain]]:
    rows = await db.execute(
        select(Objective, Domain)
        .join(Domain, Domain.id == Objective.domain_id)
        .where(Domain.exam_version_id == exam.id)
        .order_by(Domain.position, Objective.position)
    )
    return [(objective, domain) for objective, domain in rows.all()]


async def _objective(db: AsyncSession, exam: ExamVersion, code: str) -> tuple[Objective, Domain]:
    for objective, domain in await _objectives(db, exam):
        if objective.code == code:
            return objective, domain
    raise NotFoundError("objective not found")


async def _certification(db: AsyncSession, exam: ExamVersion) -> str:
    cert = await db.get(Certification, exam.certification_id)
    return cert.name if cert else ""


async def _lectures(
    db: AsyncSession, exam: ExamVersion, objective_id: int, catalog: CatalogCache, cert: str
) -> list[PathLecture]:
    rows = await db.execute(
        select(LectureObjective, IndexedLecture)
        .join(
            IndexedLecture,
            (IndexedLecture.course_slug == LectureObjective.course_slug)
            & (IndexedLecture.lecture_path == LectureObjective.lecture_path),
        )
        .where(
            LectureObjective.exam_version_id == exam.id,
            LectureObjective.objective_id == objective_id,
            LectureObjective.source != "excluded",
        )
    )
    currencies: dict[str, str] = {}
    lectures: list[PathLecture] = []
    for mapping, lecture in rows.all():
        if lecture.course_slug not in currencies:
            course = catalog.by_slug(lecture.course_slug)
            currencies[lecture.course_slug] = (
                currency(course, exam, certification=cert) if course else "unknown"
            )
        lectures.append(
            PathLecture(
                course_slug=lecture.course_slug,
                course_title=lecture.course_title,
                lecture_path=lecture.lecture_path,
                lecture_title=lecture.lecture_title,
                section_title=lecture.section_title,
                minutes=(lecture.duration_seconds or 0.0) / 60,
                score=mapping.normalized,
                source=mapping.source,
                currency=currencies[lecture.course_slug],
            )
        )
    return lectures


async def _owner_rows(
    db: AsyncSession, exam: ExamVersion, objective_id: int
) -> tuple[list[Key], set[Key]]:
    rows = (
        await db.scalars(
            select(ObjectivePathEntry)
            .where(
                ObjectivePathEntry.exam_version_id == exam.id,
                ObjectivePathEntry.objective_id == objective_id,
                ObjectivePathEntry.source.in_(("pinned", "excluded")),
            )
            .order_by(ObjectivePathEntry.position)
        )
    ).all()
    pinned = [(r.course_slug, r.lecture_path) for r in rows if r.source == "pinned"]
    excluded = {(r.course_slug, r.lecture_path) for r in rows if r.source == "excluded"}
    return pinned, excluded


async def _compose_one(
    db: AsyncSession, catalog: CatalogCache, exam: ExamVersion, objective: Objective, cert: str
) -> None:
    pinned, excluded = await _owner_rows(db, exam, objective.id)
    lectures = await _lectures(db, exam, objective.id, catalog, cert)
    entries = compose_path(lectures, pinned=pinned, excluded=excluded)
    await db.execute(
        delete(ObjectivePathEntry).where(
            ObjectivePathEntry.exam_version_id == exam.id,
            ObjectivePathEntry.objective_id == objective.id,
            ObjectivePathEntry.source != "excluded",
        )
    )
    for position, entry in enumerate(entries):
        db.add(
            ObjectivePathEntry(
                exam_version_id=exam.id,
                objective_id=objective.id,
                course_slug=entry.course_slug,
                lecture_path=entry.lecture_path,
                position=position,
                source=entry.source,
                reason=entry.reason,
                minutes=round(entry.minutes, 1),
            )
        )
    await db.flush()


async def compose_paths(
    db: AsyncSession, catalog: CatalogCache, exam: ExamVersion, *, now: datetime
) -> PathsView:
    """Recompose every objective's path from the index; the owner's rows stay."""
    cert = await _certification(db, exam)
    for objective, _ in await _objectives(db, exam):
        await _compose_one(db, catalog, exam, objective, cert)
    return await path_summaries(db, exam)


async def _completed(db: AsyncSession, keys: set[Key]) -> set[Key]:
    if not keys:
        return set()
    rows = await db.execute(
        select(CourseProgress.course_slug, CourseProgress.lecture_path).where(
            CourseProgress.completed_at.is_not(None),
            CourseProgress.course_slug.in_({slug for slug, _ in keys}),
        )
    )
    return {(slug, path) for slug, path in rows.all() if (slug, path) in keys}


async def _rows(
    db: AsyncSession, exam: ExamVersion, objective_id: int
) -> list[tuple[ObjectivePathEntry, IndexedLecture]]:
    rows = await db.execute(
        select(ObjectivePathEntry, IndexedLecture)
        .join(
            IndexedLecture,
            (IndexedLecture.course_slug == ObjectivePathEntry.course_slug)
            & (IndexedLecture.lecture_path == ObjectivePathEntry.lecture_path),
        )
        .where(
            ObjectivePathEntry.exam_version_id == exam.id,
            ObjectivePathEntry.objective_id == objective_id,
        )
        .order_by(ObjectivePathEntry.position, ObjectivePathEntry.id)
    )
    return [(entry, lecture) for entry, lecture in rows.all()]


async def objective_path(
    db: AsyncSession, catalog: CatalogCache, exam: ExamVersion, code: str
) -> ObjectivePathView:
    objective, domain = await _objective(db, exam, code)
    rows = await _rows(db, exam, objective.id)
    active = [(e, lec) for e, lec in rows if e.source != "excluded"]
    done = await _completed(db, {(e.course_slug, e.lecture_path) for e, _ in active})
    entries = [
        PathEntryView(
            position=position,
            course_slug=entry.course_slug,
            course_title=lecture.course_title,
            lecture_path=entry.lecture_path,
            lecture_title=lecture.lecture_title,
            section_title=lecture.section_title,
            minutes=entry.minutes if entry.minutes > 0 else None,
            reason=entry.reason,
            source="pinned" if entry.source == "pinned" else "proposed",
            completed=(entry.course_slug, entry.lecture_path) in done,
        )
        for position, (entry, lecture) in enumerate(active)
    ]
    courses: list[str] = []
    for view in entries:
        if view.course_title not in courses:
            courses.append(view.course_title)
    resume = next((view.position for view in entries if not view.completed), None)
    composed = [e.updated_at for e, _ in rows if e.source == "proposed" and e.updated_at]
    lectures = await _lectures(db, exam, objective.id, catalog, await _certification(db, exam))
    return ObjectivePathView(
        objective_code=objective.code,
        objective_title=objective.title,
        domain_code=domain.code,
        entries=entries,
        excluded=[
            ExcludedEntryView(
                course_slug=e.course_slug,
                course_title=lec.course_title,
                lecture_path=e.lecture_path,
                lecture_title=lec.lecture_title,
            )
            for e, lec in rows
            if e.source == "excluded"
        ],
        stale_courses=stale_courses(lectures),
        total_minutes=round(sum(view.minutes or 0.0 for view in entries), 1),
        courses=courses,
        composed_at=max(composed) if composed else None,
        resume_position=resume,
    )


async def path_summaries(db: AsyncSession, exam: ExamVersion) -> PathsView:
    """Entries, minutes and what is watched, per objective; the Progress and Learn pages' link."""
    rows = (
        await db.scalars(
            select(ObjectivePathEntry).where(
                ObjectivePathEntry.exam_version_id == exam.id,
                ObjectivePathEntry.source != "excluded",
            )
        )
    ).all()
    by_objective: dict[int, list[ObjectivePathEntry]] = defaultdict(list)
    for row in rows:
        by_objective[row.objective_id].append(row)
    done = await _completed(db, {(r.course_slug, r.lecture_path) for r in rows})
    composed = [r.updated_at for r in rows if r.source == "proposed" and r.updated_at]
    summaries = [
        PathSummaryView(
            objective_code=objective.code,
            objective_title=objective.title,
            domain_code=domain.code,
            entries=len(by_objective[objective.id]),
            completed=sum(
                1 for r in by_objective[objective.id] if (r.course_slug, r.lecture_path) in done
            ),
            total_minutes=round(sum(r.minutes for r in by_objective[objective.id]), 1),
        )
        for objective, domain in await _objectives(db, exam)
    ]
    return PathsView(
        exam_version_id=exam.id,
        composed_at=max(composed) if composed else None,
        objectives=summaries,
    )


async def decide_path(
    db: AsyncSession,
    catalog: CatalogCache,
    exam: ExamVersion,
    code: str,
    decision: PathDecision,
    *,
    now: datetime,
) -> ObjectivePathView:
    """Apply the owner's order, exclusions and restorations, then recompose the objective."""
    objective, _ = await _objective(db, exam, code)
    owned = (
        ObjectivePathEntry.exam_version_id == exam.id,
        ObjectivePathEntry.objective_id == objective.id,
    )
    if decision.reset:
        await db.execute(delete(ObjectivePathEntry).where(*owned))
    for key in decision.restore:
        await db.execute(
            delete(ObjectivePathEntry).where(
                *owned,
                ObjectivePathEntry.course_slug == key[0],
                ObjectivePathEntry.lecture_path == key[1],
                ObjectivePathEntry.source == "excluded",
            )
        )
    if decision.order:
        await db.execute(
            delete(ObjectivePathEntry).where(*owned, ObjectivePathEntry.source != "excluded")
        )
        for position, key in enumerate(decision.order):
            db.add(
                ObjectivePathEntry(
                    exam_version_id=exam.id,
                    objective_id=objective.id,
                    course_slug=key[0],
                    lecture_path=key[1],
                    position=position,
                    source="pinned",
                    reason="pinned by you",
                )
            )
    for key in decision.exclude:
        await db.execute(
            delete(ObjectivePathEntry).where(
                *owned,
                ObjectivePathEntry.course_slug == key[0],
                ObjectivePathEntry.lecture_path == key[1],
            )
        )
        db.add(
            ObjectivePathEntry(
                exam_version_id=exam.id,
                objective_id=objective.id,
                course_slug=key[0],
                lecture_path=key[1],
                position=0,
                source="excluded",
                reason="excluded by you",
            )
        )
    await db.flush()
    await _compose_one(db, catalog, exam, objective, await _certification(db, exam))
    return await objective_path(db, catalog, exam, code)


async def path_lecture_candidate(
    db: AsyncSession, exam: ExamVersion, evidence: tuple[ObjectiveEvidence, ...]
) -> LectureCandidate | None:
    """The next unwatched lecture on the weakest objective's path, for the daily plan."""
    weakest = weakest_objectives(evidence)
    if not weakest:
        return None
    objectives = {objective.code: objective for objective, _ in await _objectives(db, exam)}
    objective = objectives.get(weakest[0].code)
    if objective is None:
        return None
    rows = [(e, lec) for e, lec in await _rows(db, exam, objective.id) if e.source != "excluded"]
    done = await _completed(db, {(e.course_slug, e.lecture_path) for e, _ in rows})
    for entry, lecture in rows:
        if (entry.course_slug, entry.lecture_path) in done:
            continue
        return LectureCandidate(
            course_slug=entry.course_slug,
            lecture_path=entry.lecture_path,
            title=lecture.lecture_title,
            course_title=lecture.course_title,
            objective_code=objective.code,
            minutes=round(entry.minutes) or 8,
        )
    return None
