"""Watch: list courses from the learning share, stream a lecture, serve its captions."""

from __future__ import annotations

from pathlib import Path

import anyio
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import FileResponse, PlainTextResponse

from app.contracts.courses import (
    CatalogStatus,
    CourseSummary,
    CoursesView,
    CourseView,
    LectureProgressView,
    LectureView,
    ProgressUpdate,
    SectionView,
)
from app.corpus.captions import srt_to_vtt
from app.deps import ClockDep, DbSession, require_auth
from app.domain.exceptions import NotFoundError
from app.domain.watch import MEDIA_TYPES, Course, Lecture
from app.services.catalog import CatalogCache
from app.services.watch_progress import (
    completed_counts,
    last_watched,
    progress_for_course,
    save_progress,
)

router = APIRouter(dependencies=[Depends(require_auth)])


def _catalog(request: Request) -> CatalogCache:
    catalog: CatalogCache = request.app.state.catalog
    return catalog


def _status(catalog: CatalogCache) -> CatalogStatus:
    return CatalogStatus(
        configured=catalog.configured,
        root=str(catalog.root) if catalog.root else None,
        topics=list(catalog.topics),
        scanned_at=catalog.scanned_at,
        scanning=catalog.scanning,
        course_count=len(catalog.courses),
    )


def _course_or_404(catalog: CatalogCache, slug: str) -> Course:
    course = catalog.by_slug(slug)
    if course is None:
        raise NotFoundError("course not found")
    return course


def _lecture_or_404(course: Course, path: str) -> Lecture:
    """Only paths the catalog itself reported are ever opened; nothing else resolves."""
    lecture = course.lecture(path)
    if lecture is None:
        raise NotFoundError("lecture not found")
    return lecture


def _on_disk(course: Course, relative: str) -> Path:
    root = Path(course.root).resolve()
    target = (root / relative).resolve()
    if not target.is_relative_to(root) or not target.is_file():
        raise NotFoundError("file not found")
    return target


@router.get("", response_model=CoursesView)
async def list_courses(request: Request, db: DbSession) -> CoursesView:
    catalog = _catalog(request)
    if catalog.configured and catalog.scanned_at is None and not catalog.scanning:
        request.app.state.catalog_task = catalog.start_background_refresh()
    completed = await completed_counts(db)
    latest = await last_watched(db)
    courses: list[CourseSummary] = []
    for course in catalog.courses:
        resume = latest.get(course.slug)
        resume_lecture = course.lecture(resume.lecture_path) if resume else None
        courses.append(
            CourseSummary(
                slug=course.slug,
                title=course.title,
                topic=course.topic,
                exam_code=course.exam_code,
                year=course.year,
                lecture_count=course.lecture_count,
                caption_count=course.caption_count,
                completed_count=completed.get(course.slug, 0),
                resume_path=resume_lecture.path if resume_lecture else None,
                resume_title=resume_lecture.title if resume_lecture else None,
            )
        )
    return CoursesView(status=_status(catalog), courses=courses)


@router.post("/refresh", response_model=CatalogStatus)
async def refresh(request: Request) -> CatalogStatus:
    catalog = _catalog(request)
    request.app.state.catalog_task = catalog.start_background_refresh()
    return _status(catalog)


@router.get("/{slug}", response_model=CourseView)
async def read_course(slug: str, request: Request, db: DbSession) -> CourseView:
    course = _course_or_404(_catalog(request), slug)
    progress = await progress_for_course(db, slug)
    sections = [
        SectionView(
            title=section.title,
            lectures=[
                LectureView(
                    path=lecture.path,
                    title=lecture.title,
                    has_captions=lecture.caption_path is not None,
                    size_bytes=lecture.size_bytes,
                    progress=(
                        LectureProgressView.model_validate(progress[lecture.path])
                        if lecture.path in progress
                        else None
                    ),
                )
                for lecture in section.lectures
            ],
        )
        for section in course.sections
    ]
    return CourseView(
        slug=course.slug,
        title=course.title,
        topic=course.topic,
        exam_code=course.exam_code,
        year=course.year,
        lecture_count=course.lecture_count,
        completed_count=sum(1 for row in progress.values() if row.completed_at is not None),
        sections=sections,
    )


@router.get("/{slug}/media")
async def media(slug: str, request: Request, path: str = Query(min_length=1)) -> FileResponse:
    """The video file itself. Starlette honours Range headers, so seeking works."""
    course = _course_or_404(_catalog(request), slug)
    lecture = _lecture_or_404(course, path)
    target = await anyio.to_thread.run_sync(_on_disk, course, lecture.path)
    media_type = MEDIA_TYPES.get(target.suffix.lower(), "application/octet-stream")
    return FileResponse(target, media_type=media_type, content_disposition_type="inline")


@router.get("/{slug}/captions", response_class=PlainTextResponse)
async def captions(
    slug: str, request: Request, path: str = Query(min_length=1)
) -> PlainTextResponse:
    """The lecture's subtitle track as WebVTT (SRT converted on the fly)."""
    course = _course_or_404(_catalog(request), slug)
    lecture = _lecture_or_404(course, path)
    if lecture.caption_path is None:
        raise NotFoundError("this lecture has no captions")
    target = await anyio.to_thread.run_sync(_on_disk, course, lecture.caption_path)
    text = await anyio.to_thread.run_sync(
        lambda: target.read_text(encoding="utf-8", errors="replace")
    )
    body = text if target.suffix.lower() == ".vtt" else srt_to_vtt(text)
    return PlainTextResponse(body, media_type="text/vtt")


@router.put("/{slug}/progress", response_model=LectureProgressView)
async def update_progress(
    slug: str, req: ProgressUpdate, request: Request, db: DbSession, clock: ClockDep
) -> LectureProgressView:
    course = _course_or_404(_catalog(request), slug)
    lecture = _lecture_or_404(course, req.lecture_path)
    row = await save_progress(
        db,
        course.slug,
        lecture.path,
        position_seconds=req.position_seconds,
        duration_seconds=req.duration_seconds,
        completed=req.completed,
        now=clock.now(),
    )
    return LectureProgressView.model_validate(row)
