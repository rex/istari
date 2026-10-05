"""SQL aggregates behind the Progress view. Each function answers one question."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import (
    Answer,
    ContentItem,
    ContentItemObjective,
    ContentPack,
    ContentRevision,
    ItemProgress,
    Objective,
)


@dataclass(slots=True)
class ObjectiveCounts:
    lessons_total: int = 0
    lessons_completed: int = 0
    questions_total: int = 0
    families_seen: int = 0
    first_attempts: int = 0
    first_correct: int = 0
    repeat_attempts: int = 0
    repeat_correct: int = 0
    assessment_attempts: int = 0
    assessment_correct: int = 0


@dataclass(slots=True)
class AnswerFacts:
    """One answer, with the objectives of its item, for in-memory aggregation."""

    family_key: str
    is_correct: bool
    first_attempt: bool
    session_kind: str
    objectives: list[str] = field(default_factory=list)


async def answer_facts(db: AsyncSession, *, exam_version_id: int) -> list[AnswerFacts]:
    """Answers on active items of this track, with objective codes attached."""
    rows = await db.execute(
        select(
            Answer.id,
            Answer.family_key,
            Answer.is_correct,
            Answer.first_attempt,
            Answer.session_kind,
            Objective.code,
        )
        .join(ContentItem, ContentItem.id == Answer.item_id)
        .join(ContentPack, ContentPack.id == ContentItem.pack_id)
        .outerjoin(ContentItemObjective, ContentItemObjective.item_id == ContentItem.id)
        .outerjoin(Objective, Objective.id == ContentItemObjective.objective_id)
        .where(ContentPack.exam_version_id == exam_version_id, ContentItem.status != "invalidated")
        .order_by(Answer.id)
    )
    by_id: dict[int, AnswerFacts] = {}
    for answer_id, family, correct, first, kind, code in rows.all():
        fact = by_id.get(answer_id)
        if fact is None:
            fact = AnswerFacts(family, bool(correct), bool(first), kind)
            by_id[answer_id] = fact
        if code is not None:
            fact.objectives.append(code)
    return list(by_id.values())


async def item_counts_by_objective(
    db: AsyncSession, *, exam_version_id: int
) -> dict[str, ObjectiveCounts]:
    rows = await db.execute(
        select(
            Objective.code,
            ContentItem.kind,
            func.count(ContentItem.id),
            func.count(ItemProgress.completed_at),
        )
        .join(ContentItemObjective, ContentItemObjective.objective_id == Objective.id)
        .join(ContentItem, ContentItem.id == ContentItemObjective.item_id)
        .join(ContentPack, ContentPack.id == ContentItem.pack_id)
        .join(
            ContentRevision,
            (ContentRevision.item_id == ContentItem.id) & ContentRevision.is_current.is_(True),
        )
        .outerjoin(ItemProgress, ItemProgress.item_id == ContentItem.id)
        .where(ContentPack.exam_version_id == exam_version_id, ContentItem.status == "active")
        .group_by(Objective.code, ContentItem.kind)
    )
    counts: dict[str, ObjectiveCounts] = defaultdict(ObjectiveCounts)
    for code, kind, total, completed in rows.all():
        bucket = counts[code]
        if kind == "lesson":
            bucket.lessons_total, bucket.lessons_completed = int(total), int(completed)
        elif kind == "question":
            bucket.questions_total = int(total)
    return counts


async def invalidation_flags(db: AsyncSession, *, exam_version_id: int) -> tuple[int, int]:
    items = await db.scalar(
        select(func.count(ContentItem.id))
        .join(ContentPack, ContentPack.id == ContentItem.pack_id)
        .where(ContentPack.exam_version_id == exam_version_id, ContentItem.status == "invalidated")
    )
    answers = await db.scalar(
        select(func.count(Answer.id))
        .join(ContentItem, ContentItem.id == Answer.item_id)
        .where(ContentItem.status == "invalidated")
    )
    return int(items or 0), int(answers or 0)
