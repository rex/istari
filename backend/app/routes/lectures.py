"""The lecture-to-objective index: build it, review it, look it up."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, status

from app.contracts.comparison import CourseComparisonView
from app.contracts.lecture_review import CourseDecision, ReviewDecision, ReviewQueueView
from app.contracts.lectures import (
    IndexStatusView,
    LectureMappingView,
    ObjectiveLecturesView,
    ReviewLectureView,
)
from app.deps import ActiveExam, ClockDep, DbSession, require_auth
from app.services.catalog import CatalogCache
from app.services.course_comparison import course_comparison
from app.services.lecture_index import IndexRunner
from app.services.lecture_mapping import (
    index_status,
    lecture_mappings,
    objective_lectures,
    record_decision,
)
from app.services.lecture_queue import decide_course, review_queue

router = APIRouter(dependencies=[Depends(require_auth)])


def _catalog(request: Request) -> CatalogCache:
    catalog: CatalogCache = request.app.state.catalog
    return catalog


def _runner(request: Request) -> IndexRunner:
    runner = getattr(request.app.state, "lecture_index", None)
    if runner is None:
        runner = IndexRunner()
        request.app.state.lecture_index = runner
    return runner


@router.get("", response_model=IndexStatusView)
async def status_view(request: Request, db: DbSession, exam: ActiveExam) -> IndexStatusView:
    return await index_status(db, exam, _catalog(request), _runner(request))


@router.post("/rebuild", response_model=IndexStatusView, status_code=status.HTTP_202_ACCEPTED)
async def rebuild(
    request: Request, db: DbSession, exam: ActiveExam, clock: ClockDep
) -> IndexStatusView:
    """Start a build for the active track in the background; the status says when it ends."""
    runner = _runner(request)
    runner.start(request.app.state.session_factory, _catalog(request), exam.id, clock)
    return await index_status(db, exam, _catalog(request), runner)


@router.get("/review", response_model=ReviewQueueView)
async def next_to_review(
    request: Request,
    db: DbSession,
    exam: ActiveExam,
    after_course: str | None = Query(default=None),
    after_path: str | None = Query(default=None),
) -> ReviewQueueView:
    after = (after_course, after_path) if after_course and after_path else None
    return await review_queue(db, exam, _catalog(request), after=after)


@router.post("/review", response_model=ReviewLectureView)
async def decide(
    req: ReviewDecision, db: DbSession, exam: ActiveExam, clock: ClockDep
) -> ReviewLectureView:
    return await record_decision(db, exam, req, now=clock.now())


@router.post("/review/course", response_model=ReviewQueueView)
async def decide_whole(
    req: CourseDecision, request: Request, db: DbSession, exam: ActiveExam, clock: ClockDep
) -> ReviewQueueView:
    """Accept or exclude every unreviewed lecture of a course or section, then the next."""
    await decide_course(db, exam, req, now=clock.now())
    return await review_queue(db, exam, _catalog(request))


@router.get("/lectures/{course_slug}", response_model=list[LectureMappingView])
async def lecture_objectives(
    course_slug: str, db: DbSession, exam: ActiveExam, path: str = Query(min_length=1)
) -> list[LectureMappingView]:
    return await lecture_mappings(db, exam.id, (course_slug, path))


@router.get("/objectives/{code}", response_model=ObjectiveLecturesView)
async def lectures_for_objective(
    code: str, db: DbSession, exam: ActiveExam
) -> ObjectiveLecturesView:
    return await objective_lectures(db, exam, code)


@router.get("/courses", response_model=CourseComparisonView)
async def compare_courses(
    request: Request, db: DbSession, exam: ActiveExam
) -> CourseComparisonView:
    """Every candidate course of the track with its coverage per domain, depth and currency."""
    catalog = _catalog(request)
    if catalog.configured and catalog.scanned_at is None and not catalog.scanning:
        request.app.state.catalog_task = catalog.start_background_refresh()
    return await course_comparison(db, catalog, exam)
