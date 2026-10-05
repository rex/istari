"""Create, edit and list review cards. Duplicates are prevented by source."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import ContentItem, Note, ReviewCard, UserSettings
from app.contracts.common import ObjectiveRef
from app.contracts.review import CardCreateRequest, CardListResponse, CardPatch, CardView
from app.domain.exceptions import ConflictError, NotFoundError, ValidationError
from app.services.content_query import get_item, objective_codes_for_items, objective_refs
from app.services.reviews import card_view
from app.services.scheduler_config import build_scheduler, get_default_config


async def _view(
    db: AsyncSession,
    card: ReviewCard,
    *,
    now: datetime,
    tz: str,
    objective_map: dict[str, ObjectiveRef],
) -> CardView:
    scheduler = build_scheduler(await get_default_config(db))
    item_key: str | None = None
    codes: list[str] = []
    if card.source_item_id is not None:
        item = await db.get(ContentItem, card.source_item_id)
        if item is not None:
            item_key = item.item_key
            codes = (await objective_codes_for_items(db, [item.id])).get(item.id, [])
    return card_view(
        card,
        now=now,
        tz=tz,
        scheduler=scheduler,
        objectives=objective_refs(codes, objective_map),
        item_key=item_key,
    )


async def create_card(
    db: AsyncSession,
    *,
    req: CardCreateRequest,
    settings: UserSettings,
    now: datetime,
    objective_map: dict[str, ObjectiveRef],
) -> tuple[CardView, bool]:
    """Returns (card, created). An existing card for the same source is returned, not duplicated."""
    source_item_id: int | None = None
    source_note_id: int | None = None
    if req.source_kind == "mistake":
        if not req.item_key:
            raise ValidationError("item_key is required for a mistake card")
        item, _rev = await get_item(db, req.item_key, kind="question")
        source_item_id = item.id
    elif req.source_kind == "note":
        if req.note_id is None:
            raise ValidationError("note_id is required for a note card")
        note = await db.get(Note, req.note_id)
        if note is None:
            raise NotFoundError("note not found")
        source_note_id = note.id
    elif req.source_kind == "flashcard":
        raise ValidationError("pack flashcards are created by import, not by hand")

    existing = None
    if source_item_id is not None:
        existing = await db.scalar(
            select(ReviewCard).where(
                ReviewCard.source_kind == req.source_kind,
                ReviewCard.source_item_id == source_item_id,
            )
        )
    elif source_note_id is not None:
        existing = await db.scalar(
            select(ReviewCard).where(ReviewCard.source_note_id == source_note_id)
        )
    if existing is not None:
        return await _view(
            db, existing, now=now, tz=settings.timezone, objective_map=objective_map
        ), False

    config = await get_default_config(db)
    scheduler = build_scheduler(config)
    state = scheduler.new_card(now)
    card = ReviewCard(
        source_kind=req.source_kind,
        source_item_id=source_item_id,
        source_note_id=source_note_id,
        front_md=req.front_md,
        back_md=req.back_md,
        user_edited=True,
        state=state.state,
        step=state.step,
        stability=state.stability,
        difficulty=state.difficulty,
        due=state.due,
        last_review=state.last_review,
        scheduler_config_id=config.id,
        scheduler_version=scheduler.version,
    )
    db.add(card)
    await db.flush()
    return await _view(db, card, now=now, tz=settings.timezone, objective_map=objective_map), True


async def update_card(
    db: AsyncSession,
    *,
    card_id: int,
    patch: CardPatch,
    settings: UserSettings,
    now: datetime,
    objective_map: dict[str, ObjectiveRef],
) -> CardView:
    card = await db.get(ReviewCard, card_id)
    if card is None:
        raise NotFoundError("card not found")
    if patch.front_md is not None:
        card.front_md, card.user_edited = patch.front_md, True
    if patch.back_md is not None:
        card.back_md, card.user_edited = patch.back_md, True
    if patch.suspended is not None:
        card.suspended = patch.suspended
    await db.flush()
    return await _view(db, card, now=now, tz=settings.timezone, objective_map=objective_map)


async def delete_card(db: AsyncSession, *, card_id: int) -> None:
    card = await db.get(ReviewCard, card_id)
    if card is None:
        raise NotFoundError("card not found")
    if card.source_kind == "flashcard":
        raise ConflictError("pack flashcards cannot be deleted; suspend the card instead")
    await db.delete(card)
    await db.flush()


async def list_cards(
    db: AsyncSession,
    *,
    settings: UserSettings,
    now: datetime,
    objective_map: dict[str, ObjectiveRef],
    limit: int = 200,
) -> CardListResponse:
    total = int(await db.scalar(select(func.count(ReviewCard.id))) or 0)
    cards = (
        await db.scalars(
            select(ReviewCard).order_by(ReviewCard.due.asc(), ReviewCard.id).limit(limit)
        )
    ).all()
    views = [
        await _view(db, c, now=now, tz=settings.timezone, objective_map=objective_map)
        for c in cards
    ]
    return CardListResponse(cards=views, total=total)
