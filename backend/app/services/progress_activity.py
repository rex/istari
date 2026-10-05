"""Activity and review aggregates behind the Progress view (cards, streaks, mistakes)."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import (
    Answer,
    ContentItem,
    ContentItemObjective,
    ContentPack,
    ContentRevision,
    Domain,
    ItemProgress,
    Objective,
    ReviewCard,
    ReviewEvent,
)
from app.domain.timeframes import local_date


async def card_counts(db: AsyncSession, *, now: datetime) -> tuple[int, int]:
    total = await db.scalar(select(func.count(ReviewCard.id)))
    due = await db.scalar(
        select(func.count(ReviewCard.id)).where(
            ReviewCard.due <= now, ReviewCard.suspended.is_(False)
        )
    )
    return int(total or 0), int(due or 0)


async def activity_by_day(
    db: AsyncSession, *, now: datetime, tz: str, days: int = 14
) -> dict[str, dict[str, int]]:
    """Counts keyed by local ISO date: answers, reviews, lessons completed."""
    since = now - timedelta(days=days + 1)
    out: dict[str, dict[str, int]] = defaultdict(lambda: {"answers": 0, "reviews": 0, "lessons": 0})
    for stamp in (
        await db.scalars(select(Answer.answered_at).where(Answer.answered_at >= since))
    ).all():
        out[local_date(stamp, tz).isoformat()]["answers"] += 1
    for reviewed in (
        await db.scalars(select(ReviewEvent.reviewed_at).where(ReviewEvent.reviewed_at >= since))
    ).all():
        out[local_date(reviewed, tz).isoformat()]["reviews"] += 1
    for completed in (
        await db.scalars(
            select(ItemProgress.completed_at).where(ItemProgress.completed_at >= since)
        )
    ).all():
        if completed is not None:
            out[local_date(completed, tz).isoformat()]["lessons"] += 1
    return out


async def assessment_session_count(db: AsyncSession) -> int:
    count = await db.scalar(
        select(func.count(func.distinct(Answer.session_id))).where(
            Answer.session_kind == "assessment"
        )
    )
    return int(count or 0)


async def confident_mistakes(
    db: AsyncSession, *, exam_version_id: int, limit: int = 10
) -> list[tuple[Answer, ContentItem, ContentRevision, bool]]:
    """Latest confident-wrong answer per item, newest first, with has_card."""
    latest = (
        select(Answer.item_id, func.max(Answer.answered_at).label("at"))
        .where(Answer.confidence == "confident", Answer.is_correct.is_(False))
        .group_by(Answer.item_id)
        .subquery()
    )
    has_card = (
        select(ReviewCard.source_item_id).where(ReviewCard.source_kind == "mistake").subquery()
    )
    rows = await db.execute(
        select(
            Answer,
            ContentItem,
            ContentRevision,
            case((has_card.c.source_item_id.is_not(None), True), else_=False),
        )
        .join(latest, (latest.c.item_id == Answer.item_id) & (latest.c.at == Answer.answered_at))
        .join(ContentItem, ContentItem.id == Answer.item_id)
        .join(ContentPack, ContentPack.id == ContentItem.pack_id)
        .join(ContentRevision, ContentRevision.id == Answer.revision_id)
        .outerjoin(has_card, has_card.c.source_item_id == ContentItem.id)
        .where(ContentPack.exam_version_id == exam_version_id, ContentItem.status == "active")
        .order_by(Answer.answered_at.desc())
        .limit(limit)
    )
    return [(a, i, r, bool(c)) for a, i, r, c in rows.all()]


async def lesson_counts(
    db: AsyncSession, *, exam_version_id: int
) -> tuple[tuple[int, int], dict[str, tuple[int, int]]]:
    """Distinct lessons as (total, completed): overall, then per domain code.

    A lesson that teaches several objectives is counted once, never once per objective,
    so the summary cannot claim more lessons than the pack contains.
    """
    per_lesson = (
        select(
            Domain.code.label("domain"),
            ContentItem.id.label("item_id"),
            func.bool_or(ItemProgress.completed_at.is_not(None)).label("done"),
        )
        .join(ContentItemObjective, ContentItemObjective.item_id == ContentItem.id)
        .join(Objective, Objective.id == ContentItemObjective.objective_id)
        .join(Domain, Domain.id == Objective.domain_id)
        .join(ContentPack, ContentPack.id == ContentItem.pack_id)
        .outerjoin(ItemProgress, ItemProgress.item_id == ContentItem.id)
        .where(
            ContentPack.exam_version_id == exam_version_id,
            ContentItem.kind == "lesson",
            ContentItem.status == "active",
        )
        .group_by(Domain.code, ContentItem.id)
        .subquery()
    )
    by_domain_rows = await db.execute(
        select(
            per_lesson.c.domain,
            func.count(per_lesson.c.item_id),
            func.sum(case((per_lesson.c.done, 1), else_=0)),
        ).group_by(per_lesson.c.domain)
    )
    by_domain = {str(code): (int(total), int(done or 0)) for code, total, done in by_domain_rows}
    total, completed = (
        await db.execute(
            select(
                func.count(func.distinct(per_lesson.c.item_id)),
                func.count(func.distinct(case((per_lesson.c.done, per_lesson.c.item_id)))),
            )
        )
    ).one()
    return (int(total or 0), int(completed or 0)), by_domain
