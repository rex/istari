"""Per-track counts and progress for the course picker, over every track at once.

Counts are the pack's active items by kind. Progress is coverage and says so (lessons read,
question families seen, labs verified on the first graded attempt); `last_studied_at` is the
latest answer, review, lesson opening or lab attempt on the track's items.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import (
    Answer,
    ContentItem,
    ContentPack,
    ItemProgress,
    LabAttempt,
    ReviewCard,
    ReviewEvent,
)
from app.contracts.track import TrackCounts, TrackProgress
from app.domain.track_progress import TrackTally, coverage_fraction, progress_sentence
from app.services.lab_progress import lab_facts


@dataclass(slots=True)
class _Answers:
    families: set[str] = field(default_factory=set)
    first_attempts: int = 0
    first_correct: int = 0


async def _item_counts(db: AsyncSession) -> dict[int, dict[str, tuple[int, int]]]:
    """exam version -> kind -> (active items, items completed)."""
    rows = await db.execute(
        select(
            ContentPack.exam_version_id,
            ContentItem.kind,
            func.count(ContentItem.id),
            func.count(ItemProgress.completed_at),
        )
        .join(ContentPack, ContentPack.id == ContentItem.pack_id)
        .outerjoin(ItemProgress, ItemProgress.item_id == ContentItem.id)
        .where(ContentItem.status == "active")
        .group_by(ContentPack.exam_version_id, ContentItem.kind)
    )
    counts: dict[int, dict[str, tuple[int, int]]] = defaultdict(dict)
    for exam_id, kind, total, completed in rows.all():
        counts[int(exam_id)][str(kind)] = (int(total), int(completed))
    return counts


async def _answers(db: AsyncSession) -> dict[int, _Answers]:
    rows = await db.execute(
        select(
            ContentPack.exam_version_id,
            Answer.family_key,
            Answer.is_correct,
            Answer.first_attempt,
        )
        .join(ContentItem, ContentItem.id == Answer.item_id)
        .join(ContentPack, ContentPack.id == ContentItem.pack_id)
        .where(ContentItem.status != "invalidated")
    )
    agg: dict[int, _Answers] = defaultdict(_Answers)
    for exam_id, family, correct, first in rows.all():
        bucket = agg[int(exam_id)]
        bucket.families.add(str(family))
        if first:
            bucket.first_attempts += 1
            bucket.first_correct += int(bool(correct))
    return agg


async def track_tallies(db: AsyncSession, exam_version_ids: list[int]) -> dict[int, TrackTally]:
    """One tally per track: two grouped queries over all tracks plus the lab facts per track."""
    kinds = await _item_counts(db)
    answers = await _answers(db)
    tallies: dict[int, TrackTally] = {}
    for exam_id in exam_version_ids:
        by_kind = kinds.get(exam_id, {})
        answered = answers.get(exam_id, _Answers())
        labs = await lab_facts(db, exam_version_id=exam_id)
        tallies[exam_id] = TrackTally(
            lessons=by_kind.get("lesson", (0, 0))[0],
            lessons_completed=by_kind.get("lesson", (0, 0))[1],
            questions=by_kind.get("question", (0, 0))[0],
            families_seen=len(answered.families),
            first_attempts=answered.first_attempts,
            first_correct=answered.first_correct,
            cards=by_kind.get("flashcard", (0, 0))[0],
            labs=by_kind.get("lab", (0, 0))[0],
            verified_labs=len(labs),
            labs_attempted=sum(1 for lab in labs if lab.graded_attempts),
            labs_passed_first=sum(1 for lab in labs if lab.first_passed),
        )
    return tallies


async def last_studied(db: AsyncSession) -> dict[int, datetime]:
    """exam version -> the latest answer, review, lesson opening or lab attempt."""
    item_pack = ContentPack.id == ContentItem.pack_id
    answered = (
        select(ContentPack.exam_version_id, func.max(Answer.answered_at))
        .join(ContentItem, ContentItem.id == Answer.item_id)
        .join(ContentPack, item_pack)
        .group_by(ContentPack.exam_version_id)
    )
    opened = (
        select(
            ContentPack.exam_version_id,
            func.max(func.coalesce(ItemProgress.completed_at, ItemProgress.last_opened_at)),
        )
        .join(ContentItem, ContentItem.id == ItemProgress.item_id)
        .join(ContentPack, item_pack)
        .group_by(ContentPack.exam_version_id)
    )
    attempted = (
        select(
            ContentPack.exam_version_id,
            func.max(func.coalesce(LabAttempt.checked_at, LabAttempt.setup_at)),
        )
        .join(ContentItem, ContentItem.id == LabAttempt.item_id)
        .join(ContentPack, item_pack)
        .group_by(ContentPack.exam_version_id)
    )
    reviewed = (
        select(ContentPack.exam_version_id, func.max(ReviewEvent.reviewed_at))
        .join(ReviewCard, ReviewCard.id == ReviewEvent.card_id)
        .join(ContentItem, ContentItem.id == ReviewCard.source_item_id)
        .join(ContentPack, item_pack)
        .group_by(ContentPack.exam_version_id)
    )
    latest: dict[int, datetime] = {}
    for query in (answered, opened, attempted, reviewed):
        for exam_id, when in (await db.execute(query)).all():
            if when is None:
                continue
            current = latest.get(int(exam_id))
            if current is None or when > current:
                latest[int(exam_id)] = when
    return latest


def card_fields(tally: TrackTally) -> tuple[TrackCounts, TrackProgress | None]:
    """The counts line and, once anything was done on the track, its progress line."""
    counts = TrackCounts(
        lessons=tally.lessons, questions=tally.questions, cards=tally.cards, labs=tally.labs
    )
    if not tally.started:
        return counts, None
    fraction = coverage_fraction(tally)
    return counts, TrackProgress(
        fraction=fraction if fraction is not None else 0.0, sentence=progress_sentence(tally)
    )
