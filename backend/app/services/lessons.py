"""Lessons: listing, reading, progress. Completion is coverage, not mastery."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import ContentItem, ContentRevision, ItemProgress, Note, UserSettings
from app.contracts.common import ObjectiveRef
from app.contracts.lesson import (
    ItemProgressView,
    LessonCheckView,
    LessonProgressPatch,
    LessonSummary,
    LessonView,
    NoteView,
)
from app.domain.planning_types import LessonCandidate
from app.services.content_query import (
    content_list,
    content_str,
    get_item,
    list_items,
    objective_codes_for_items,
    objective_refs,
    revision_sources,
)


async def get_or_create_progress(db: AsyncSession, item_id: int) -> ItemProgress:
    row = await db.scalar(select(ItemProgress).where(ItemProgress.item_id == item_id))
    if row is None:
        row = ItemProgress(item_id=item_id)
        db.add(row)
        await db.flush()
    return row


def progress_view(row: ItemProgress | None) -> ItemProgressView:
    if row is None:
        return ItemProgressView(
            position=0.0, bookmarked=False, completed_at=None, last_opened_at=None
        )
    return ItemProgressView(
        position=row.position,
        bookmarked=row.bookmarked,
        completed_at=row.completed_at,
        last_opened_at=row.last_opened_at,
    )


def _summary(
    item: ContentItem,
    rev: ContentRevision,
    codes: list[str],
    progress: ItemProgress | None,
    objective_map: dict[str, ObjectiveRef],
    familiar: set[str],
) -> LessonSummary:
    refs = objective_refs(codes, objective_map)
    minutes = rev.content.get("estimated_minutes", 5)
    authored = rev.provenance.get("authored_by", "unknown")
    return LessonSummary(
        item_key=item.item_key,
        title=content_str(rev, "title"),
        summary=content_str(rev, "summary"),
        estimated_minutes=int(minutes) if isinstance(minutes, int) else 5,
        objectives=refs,
        domain_code=refs[0].domain_code if refs else "?",
        review_status=rev.review_status,
        authored_by=str(authored),
        progress=progress_view(progress),
        self_declared_familiar=bool(codes) and all(c in familiar for c in codes),
    )


async def list_lessons(
    db: AsyncSession,
    *,
    exam_version_id: int,
    settings: UserSettings,
    objective_map: dict[str, ObjectiveRef],
) -> list[LessonSummary]:
    rows = await list_items(db, exam_version_id=exam_version_id, kind="lesson")
    codes = await objective_codes_for_items(db, (item.id for item, _ in rows))
    progress_rows = {
        p.item_id: p
        for p in (
            await db.scalars(
                select(ItemProgress).where(
                    ItemProgress.item_id.in_([i.id for i, _ in rows] or [-1])
                )
            )
        ).all()
    }
    familiar = set(settings.familiar_objective_codes)
    summaries = [
        _summary(
            item, rev, codes.get(item.id, []), progress_rows.get(item.id), objective_map, familiar
        )
        for item, rev in rows
    ]
    order = {code: i for i, code in enumerate(objective_map)}
    summaries.sort(
        key=lambda s: (order.get(s.objectives[0].code, 999) if s.objectives else 999, s.item_key)
    )
    return summaries


async def next_unread_lesson(
    db: AsyncSession,
    *,
    exam_version_id: int,
    settings: UserSettings,
    objective_map: dict[str, ObjectiveRef],
) -> LessonCandidate | None:
    """First incomplete lesson in objective order; self-declared familiar ones go last."""
    lessons = await list_lessons(
        db, exam_version_id=exam_version_id, settings=settings, objective_map=objective_map
    )
    unread = [lesson for lesson in lessons if lesson.progress.completed_at is None]
    unread.sort(key=lambda s: s.self_declared_familiar)
    if not unread:
        return None
    first = unread[0]
    return LessonCandidate(
        item_key=first.item_key, title=first.title, estimated_minutes=first.estimated_minutes
    )


async def get_lesson(
    db: AsyncSession,
    *,
    key: str,
    settings: UserSettings,
    objective_map: dict[str, ObjectiveRef],
    now: datetime,
) -> LessonView:
    item, rev = await get_item(db, key, kind="lesson")
    codes = (await objective_codes_for_items(db, [item.id])).get(item.id, [])
    progress = await get_or_create_progress(db, item.id)
    progress.last_opened_at = now
    notes = (
        await db.scalars(select(Note).where(Note.item_id == item.id).order_by(Note.created_at))
    ).all()
    checks = [
        LessonCheckView(
            prompt_md=str(c.get("prompt_md", "")), answer_md=str(c.get("answer_md", ""))
        )
        for c in content_list(rev, "checks")
        if isinstance(c, dict)
    ]
    summary = _summary(
        item, rev, codes, progress, objective_map, set(settings.familiar_objective_codes)
    )
    return LessonView(
        **summary.model_dump(),
        body_md=content_str(rev, "body_md"),
        foundations_md=content_str(rev, "foundations_md"),
        checks=checks,
        sources=revision_sources(rev),
        notes=[note_view(n, item.item_key) for n in notes],
    )


def note_view(note: Note, item_key: str | None) -> NoteView:
    return NoteView(
        id=note.id,
        item_key=item_key,
        body_md=note.body_md,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


async def update_progress(
    db: AsyncSession, *, key: str, patch: LessonProgressPatch, now: datetime
) -> ItemProgressView:
    item, _rev = await get_item(db, key, kind="lesson")
    progress = await get_or_create_progress(db, item.id)
    if patch.position is not None:
        progress.position = patch.position
    if patch.bookmarked is not None:
        progress.bookmarked = patch.bookmarked
    if patch.completed is not None:
        progress.completed_at = now if patch.completed else None
    await db.flush()
    return progress_view(progress)
