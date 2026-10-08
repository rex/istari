"""Per-lecture playback position and completion."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import CourseProgress

COMPLETION_RATIO = 0.95


async def progress_for_course(db: AsyncSession, course_slug: str) -> dict[str, CourseProgress]:
    rows = await db.scalars(select(CourseProgress).where(CourseProgress.course_slug == course_slug))
    return {row.lecture_path: row for row in rows.all()}


async def completed_counts(db: AsyncSession) -> dict[str, int]:
    rows = await db.execute(
        select(CourseProgress.course_slug, func.count(CourseProgress.id))
        .where(CourseProgress.completed_at.is_not(None))
        .group_by(CourseProgress.course_slug)
    )
    return {str(slug): int(count) for slug, count in rows.all()}


async def last_watched(db: AsyncSession) -> dict[str, CourseProgress]:
    """The most recently watched lecture per course, for resume markers."""
    rows = await db.scalars(
        select(CourseProgress)
        .where(CourseProgress.last_watched_at.is_not(None))
        .order_by(CourseProgress.last_watched_at.desc())
    )
    latest: dict[str, CourseProgress] = {}
    for row in rows.all():
        latest.setdefault(row.course_slug, row)
    return latest


async def save_progress(
    db: AsyncSession,
    course_slug: str,
    lecture_path: str,
    *,
    position_seconds: float,
    duration_seconds: float | None,
    completed: bool,
    now: datetime,
) -> CourseProgress:
    """Upsert; a position past the completion ratio also marks the lecture complete."""
    row = await db.scalar(
        select(CourseProgress).where(
            CourseProgress.course_slug == course_slug, CourseProgress.lecture_path == lecture_path
        )
    )
    if row is None:
        try:
            async with db.begin_nested():
                row = CourseProgress(course_slug=course_slug, lecture_path=lecture_path)
                db.add(row)
                await db.flush()
        except IntegrityError:
            row = await db.scalar(
                select(CourseProgress).where(
                    CourseProgress.course_slug == course_slug,
                    CourseProgress.lecture_path == lecture_path,
                )
            )
    assert row is not None
    row.position_seconds = max(0.0, position_seconds)
    if duration_seconds is not None and duration_seconds > 0:
        row.duration_seconds = duration_seconds
    row.last_watched_at = now
    reached_end = (
        row.duration_seconds is not None
        and row.duration_seconds > 0
        and row.position_seconds >= COMPLETION_RATIO * row.duration_seconds
    )
    if (completed or reached_end) and row.completed_at is None:
        row.completed_at = now
    await db.flush()
    return row
