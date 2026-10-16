"""Read the lecture-to-objective index and record the owner's decisions on it."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import (
    Domain,
    ExamVersion,
    IndexedLecture,
    LectureIndexRun,
    LectureObjective,
    LectureReview,
    Objective,
)
from app.contracts.lectures import (
    IndexStatusView,
    LectureMappingView,
    LectureRef,
    ObjectiveLecturesView,
    ObjectiveLectureView,
    ReviewDecision,
    ReviewLectureView,
    ReviewQueueView,
)
from app.domain.exceptions import NotFoundError
from app.services.catalog import CatalogCache
from app.services.lecture_index import (
    MACHINE_SOURCES,
    IndexRunner,
    candidate_courses,
    track_subject,
)

SOURCE_RANK = {"pinned": 0, "rule": 1, "lexical": 2, "excluded": 3}
OBJECTIVE_LECTURE_LIMIT = 50

LectureKey = tuple[str, str]


def _mapping_view(
    row: LectureObjective, objective: Objective, domain: Domain
) -> LectureMappingView:
    return LectureMappingView(
        objective_code=objective.code,
        objective_title=objective.title,
        domain_code=domain.code,
        score=row.score,
        normalized=row.normalized,
        source=row.source,  # type: ignore[arg-type]
        matched_terms=[str(term) for term in row.matched_terms],
    )


def _ref(lecture: IndexedLecture) -> LectureRef:
    return LectureRef(
        course_slug=lecture.course_slug,
        course_title=lecture.course_title,
        exam_code=lecture.exam_code,
        year=lecture.year,
        lecture_path=lecture.lecture_path,
        lecture_title=lecture.lecture_title,
        section_title=lecture.section_title,
        duration_seconds=lecture.duration_seconds,
        word_count=lecture.word_count,
    )


async def _mapping_rows(
    db: AsyncSession, exam_version_id: int, key: LectureKey
) -> list[tuple[LectureObjective, Objective, Domain]]:
    rows = await db.execute(
        select(LectureObjective, Objective, Domain)
        .join(Objective, Objective.id == LectureObjective.objective_id)
        .join(Domain, Domain.id == Objective.domain_id)
        .where(
            LectureObjective.exam_version_id == exam_version_id,
            LectureObjective.course_slug == key[0],
            LectureObjective.lecture_path == key[1],
        )
    )
    return sorted(
        rows.all(), key=lambda r: (SOURCE_RANK.get(r[0].source, 9), -r[0].normalized, r[1].code)
    )


async def lecture_mappings(
    db: AsyncSession, exam_version_id: int, key: LectureKey
) -> list[LectureMappingView]:
    return [_mapping_view(*row) for row in await _mapping_rows(db, exam_version_id, key)]


async def index_status(
    db: AsyncSession, exam: ExamVersion, catalog: CatalogCache, runner: IndexRunner
) -> IndexStatusView:
    last = await db.scalar(
        select(LectureIndexRun)
        .where(LectureIndexRun.exam_version_id == exam.id)
        .order_by(LectureIndexRun.id.desc())
        .limit(1)
    )
    courses = candidate_courses(
        catalog, exam_code=exam.code, subject_slug=await track_subject(db, exam)
    )
    mappings = await db.scalar(
        select(func.count(LectureObjective.id)).where(
            LectureObjective.exam_version_id == exam.id,
            LectureObjective.source != "excluded",
        )
    )
    reviewed = await db.scalar(
        select(func.count(LectureReview.id)).where(LectureReview.exam_version_id == exam.id)
    )
    return IndexStatusView(
        exam_version_id=exam.id,
        candidate_courses=last.candidate_courses if last else len(courses),
        lectures_total=last.lectures_total if last else 0,
        lectures_with_captions=last.lectures_with_captions if last else 0,
        lectures_indexed=last.lectures_indexed if last else 0,
        mappings=int(mappings or 0),
        reviewed=int(reviewed or 0),
        running=runner.running or (last is not None and last.status == "running"),
        last_run_at=last.finished_at or last.started_at if last else None,
        last_error=(last.error if last and last.status == "failed" else None) or runner.last_error,
    )


async def _unreviewed(db: AsyncSession, exam_version_id: int) -> list[LectureKey]:
    reviewed = select(LectureReview.course_slug, LectureReview.lecture_path).where(
        LectureReview.exam_version_id == exam_version_id
    )
    rows = await db.execute(
        select(LectureObjective.course_slug, LectureObjective.lecture_path)
        .where(
            LectureObjective.exam_version_id == exam_version_id,
            LectureObjective.source.in_(MACHINE_SOURCES),
        )
        .distinct()
        .order_by(LectureObjective.course_slug, LectureObjective.lecture_path)
    )
    done = {(slug, path) for slug, path in (await db.execute(reviewed)).all()}
    return [(slug, path) for slug, path in rows.all() if (slug, path) not in done]


async def _lecture_view(
    db: AsyncSession, exam_version_id: int, key: LectureKey, *, reviewed: bool
) -> ReviewLectureView:
    lecture = await db.scalar(
        select(IndexedLecture).where(
            IndexedLecture.course_slug == key[0], IndexedLecture.lecture_path == key[1]
        )
    )
    if lecture is None:
        raise NotFoundError("lecture is not in the index")
    candidates = await lecture_mappings(db, exam_version_id, key)
    return ReviewLectureView(
        **_ref(lecture).model_dump(),
        excerpt=lecture.excerpt,
        candidates=candidates,
        reviewed=reviewed,
    )


async def review_queue(
    db: AsyncSession, exam: ExamVersion, *, after: LectureKey | None = None
) -> ReviewQueueView:
    """The next lecture the owner has not looked at, in course order, past `after`."""
    pending = await _unreviewed(db, exam.id)
    reviewed = await db.scalar(
        select(func.count(LectureReview.id)).where(LectureReview.exam_version_id == exam.id)
    )
    indexed = await db.scalar(select(func.count(IndexedLecture.id)))
    candidates = [key for key in pending if after is None or key > after] or pending
    lecture = (
        await _lecture_view(db, exam.id, candidates[0], reviewed=False) if candidates else None
    )
    return ReviewQueueView(
        lecture=lecture,
        remaining=len(pending),
        reviewed=int(reviewed or 0),
        indexed=int(indexed or 0),
    )


async def record_decision(
    db: AsyncSession, exam: ExamVersion, decision: ReviewDecision, *, now: datetime
) -> ReviewLectureView:
    """Pin the named objectives, or exclude the lecture, or accept it as ranked."""
    key = (decision.course_slug, decision.lecture_path)
    rows = await _mapping_rows(db, exam.id, key)
    by_code = {objective.code: row for row, objective, _ in rows}
    if decision.exclude:
        for row in by_code.values():
            row.source = "excluded"
        label = "excluded"
    elif decision.pin:
        objectives = {
            o.code: o
            for o in (
                await db.scalars(
                    select(Objective)
                    .join(Domain, Domain.id == Objective.domain_id)
                    .where(Domain.exam_version_id == exam.id, Objective.code.in_(decision.pin))
                )
            ).all()
        }
        missing = [code for code in decision.pin if code not in objectives]
        if missing:
            raise NotFoundError(f"unknown objective code: {', '.join(missing)}")
        for code, objective in objectives.items():
            existing = by_code.get(code)
            if existing is None:
                db.add(
                    LectureObjective(
                        exam_version_id=exam.id,
                        course_slug=key[0],
                        lecture_path=key[1],
                        objective_id=objective.id,
                        source="pinned",
                        score=1.0,
                        normalized=1.0,
                        matched_terms=[],
                    )
                )
            else:
                existing.source = "pinned"
                existing.normalized = 1.0
        label = "pinned"
    else:
        label = "accepted"
    await db.execute(
        delete(LectureReview).where(
            LectureReview.exam_version_id == exam.id,
            LectureReview.course_slug == key[0],
            LectureReview.lecture_path == key[1],
        )
    )
    db.add(
        LectureReview(
            exam_version_id=exam.id,
            course_slug=key[0],
            lecture_path=key[1],
            decision=label,
            reviewed_at=now,
        )
    )
    await db.flush()
    return await _lecture_view(db, exam.id, key, reviewed=True)


async def objective_lectures(
    db: AsyncSession, exam: ExamVersion, code: str
) -> ObjectiveLecturesView:
    """The lectures ranked under one objective: pinned first, then rules, then by score."""
    objective = await db.scalar(
        select(Objective)
        .join(Domain, Domain.id == Objective.domain_id)
        .where(Domain.exam_version_id == exam.id, Objective.code == code)
    )
    if objective is None:
        raise NotFoundError("objective not found")
    rows = (
        await db.execute(
            select(LectureObjective, IndexedLecture)
            .join(
                IndexedLecture,
                (IndexedLecture.course_slug == LectureObjective.course_slug)
                & (IndexedLecture.lecture_path == LectureObjective.lecture_path),
            )
            .where(
                LectureObjective.exam_version_id == exam.id,
                LectureObjective.objective_id == objective.id,
                LectureObjective.source != "excluded",
            )
        )
    ).all()
    ordered = sorted(
        rows, key=lambda r: (SOURCE_RANK.get(r[0].source, 9), -r[0].normalized, -r[0].score)
    )
    return ObjectiveLecturesView(
        objective_code=objective.code,
        objective_title=objective.title,
        lectures=[
            ObjectiveLectureView(
                **_ref(lecture).model_dump(),
                score=row.score,
                normalized=row.normalized,
                source=row.source,  # type: ignore[arg-type]
                matched_terms=[str(term) for term in row.matched_terms],
            )
            for row, lecture in ordered[:OBJECTIVE_LECTURE_LIMIT]
        ],
    )
