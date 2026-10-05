"""Due cards and ratings. All times UTC in storage; `due_local` rendered per settings."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import ContentItem, ReviewCard, ReviewEvent, UserSettings
from app.contracts.common import ObjectiveRef
from app.contracts.review import CardView, DueResponse, RateRequest, RateResponse
from app.domain.exceptions import NotFoundError
from app.domain.recommendation import RECOVERY_REVIEW_CAP
from app.domain.scheduling.interface import STATE_LEARNING, CardState, Scheduler
from app.domain.timeframes import format_local, local_day_bounds
from app.services.content_query import objective_codes_for_items, objective_refs
from app.services.scheduler_config import build_scheduler, get_default_config


def card_state(card: ReviewCard) -> CardState:
    return CardState(
        state=card.state,
        step=card.step,
        stability=card.stability,
        difficulty=card.difficulty,
        due=card.due,
        last_review=card.last_review,
    )


def _apply_state(card: ReviewCard, state: CardState) -> None:
    card.state, card.step = state.state, state.step
    card.stability, card.difficulty = state.stability, state.difficulty
    card.due, card.last_review = state.due, state.last_review


def card_view(
    card: ReviewCard,
    *,
    now: datetime,
    tz: str,
    scheduler: Scheduler,
    objectives: list[ObjectiveRef],
    item_key: str | None,
) -> CardView:
    retrievability = scheduler.retrievability(card_state(card), now) if card.last_review else None
    return CardView(
        id=card.id,
        source_kind=card.source_kind,
        source_item_key=item_key,
        source_note_id=card.source_note_id,
        front_md=card.front_md,
        back_md=card.back_md,
        objectives=objectives,
        state=card.state,
        due=card.due,
        due_local=format_local(card.due, tz),
        last_review=card.last_review,
        suspended=card.suspended,
        user_edited=card.user_edited,
        retrievability=retrievability,
    )


async def reviewed_today(db: AsyncSession, *, now: datetime, tz: str) -> int:
    start, end = local_day_bounds(now, tz)
    count = await db.scalar(
        select(func.count(ReviewEvent.id)).where(
            ReviewEvent.reviewed_at >= start, ReviewEvent.reviewed_at < end
        )
    )
    return int(count or 0)


async def due_count(db: AsyncSession, *, now: datetime) -> int:
    count = await db.scalar(
        select(func.count(ReviewCard.id)).where(
            ReviewCard.due <= now, ReviewCard.suspended.is_(False)
        )
    )
    return int(count or 0)


async def _views_for(
    db: AsyncSession,
    cards: list[ReviewCard],
    *,
    now: datetime,
    tz: str,
    scheduler: Scheduler,
    objective_map: dict[str, ObjectiveRef],
) -> list[CardView]:
    item_ids = [c.source_item_id for c in cards if c.source_item_id is not None]
    codes = await objective_codes_for_items(db, item_ids)
    keys: dict[int, str] = {}
    if item_ids:
        rows = await db.execute(
            select(ContentItem.id, ContentItem.item_key).where(ContentItem.id.in_(item_ids))
        )
        keys = dict(rows.all())
    return [
        card_view(
            c,
            now=now,
            tz=tz,
            scheduler=scheduler,
            objectives=objective_refs(codes.get(c.source_item_id or -1, []), objective_map),
            item_key=keys.get(c.source_item_id or -1),
        )
        for c in cards
    ]


async def due_cards(
    db: AsyncSession,
    *,
    settings: UserSettings,
    now: datetime,
    limit: int | None,
    objective_map: dict[str, ObjectiveRef],
) -> DueResponse:
    tz = settings.timezone
    done_today = await reviewed_today(db, now=now, tz=tz)
    remaining = max(settings.daily_review_limit - done_today, 0)
    cap = remaining if limit is None else min(limit, remaining)
    if settings.backlog_mode == "recovery":
        cap = min(cap, RECOVERY_REVIEW_CAP)
    total = await due_count(db, now=now)
    new_total = await db.scalar(
        select(func.count(ReviewCard.id)).where(
            ReviewCard.last_review.is_(None), ReviewCard.suspended.is_(False)
        )
    )
    cards = list(
        (
            await db.scalars(
                select(ReviewCard)
                .where(ReviewCard.due <= now, ReviewCard.suspended.is_(False))
                .order_by(ReviewCard.due.asc(), ReviewCard.id.asc())
                .limit(cap)
            )
        ).all()
    )
    config = await get_default_config(db)
    scheduler = build_scheduler(config)
    return DueResponse(
        cards=await _views_for(
            db, cards, now=now, tz=tz, scheduler=scheduler, objective_map=objective_map
        ),
        due_total=total,
        new_total=int(new_total or 0),
        reviewed_today=done_today,
        daily_limit=settings.daily_review_limit,
        remaining_today=remaining,
        backlog_mode=settings.backlog_mode,
        timezone=tz,
    )


async def rate_card(
    db: AsyncSession,
    *,
    card_id: int,
    req: RateRequest,
    settings: UserSettings,
    now: datetime,
    objective_map: dict[str, ObjectiveRef],
) -> RateResponse:
    card = await db.scalar(select(ReviewCard).where(ReviewCard.id == card_id).with_for_update())
    if card is None:
        raise NotFoundError("card not found")
    config = await get_default_config(db)
    scheduler = build_scheduler(config)
    tz = settings.timezone

    already = await db.scalar(
        select(ReviewEvent).where(ReviewEvent.client_request_id == req.request_id)
    )
    recorded = already is not None
    if not recorded:
        before = card_state(card)
        after = scheduler.review(before, req.rating, now, req.duration_ms)
        event = ReviewEvent(
            card_id=card.id,
            rating=req.rating,
            reviewed_at=now,
            review_duration_ms=req.duration_ms,
            due_before=before.due,
            due_after=after.due,
            state_before=before.state,
            state_after=after.state,
            stability_after=after.stability,
            difficulty_after=after.difficulty,
            scheduler_config_id=config.id,
            scheduler_version=scheduler.version,
            client_request_id=req.request_id,
        )
        try:
            async with db.begin_nested():
                db.add(event)
                await db.flush()
                _apply_state(card, after)
                card.scheduler_config_id = config.id
                card.scheduler_version = scheduler.version
        except IntegrityError:
            recorded = True
    views = await _views_for(
        db, [card], now=now, tz=tz, scheduler=scheduler, objective_map=objective_map
    )
    done_today = await reviewed_today(db, now=now, tz=tz)
    return RateResponse(
        card=views[0],
        already_recorded=recorded,
        reviewed_today=done_today,
        remaining_today=max(settings.daily_review_limit - done_today, 0),
    )


def is_new(card: ReviewCard) -> bool:
    return card.state == STATE_LEARNING and card.last_review is None
