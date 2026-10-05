"""Flashcard reviews and card management."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response, status

from app.contracts.common import OkResponse
from app.contracts.review import (
    CardCreateRequest,
    CardListResponse,
    CardPatch,
    CardView,
    DueResponse,
    RateRequest,
    RateResponse,
)
from app.deps import ClockDep, DbSession, ObjectiveMap, SettingsDep, require_auth
from app.services import cards as card_service
from app.services import reviews as review_service

router = APIRouter(dependencies=[Depends(require_auth)])


@router.get("/due", response_model=DueResponse)
async def due(
    db: DbSession,
    clock: ClockDep,
    user_settings: SettingsDep,
    objective_map: ObjectiveMap,
    limit: int | None = Query(default=None, ge=1, le=200),
) -> DueResponse:
    return await review_service.due_cards(
        db, settings=user_settings, now=clock.now(), limit=limit, objective_map=objective_map
    )


@router.post("/cards/{card_id}/rate", response_model=RateResponse)
async def rate(
    card_id: int,
    req: RateRequest,
    db: DbSession,
    clock: ClockDep,
    user_settings: SettingsDep,
    objective_map: ObjectiveMap,
) -> RateResponse:
    return await review_service.rate_card(
        db,
        card_id=card_id,
        req=req,
        settings=user_settings,
        now=clock.now(),
        objective_map=objective_map,
    )


@router.get("/cards", response_model=CardListResponse)
async def list_cards(
    db: DbSession, clock: ClockDep, user_settings: SettingsDep, objective_map: ObjectiveMap
) -> CardListResponse:
    return await card_service.list_cards(
        db, settings=user_settings, now=clock.now(), objective_map=objective_map
    )


@router.post("/cards", response_model=CardView)
async def create_card(
    req: CardCreateRequest,
    response: Response,
    db: DbSession,
    clock: ClockDep,
    user_settings: SettingsDep,
    objective_map: ObjectiveMap,
) -> CardView:
    card, created = await card_service.create_card(
        db, req=req, settings=user_settings, now=clock.now(), objective_map=objective_map
    )
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return card


@router.patch("/cards/{card_id}", response_model=CardView)
async def update_card(
    card_id: int,
    patch: CardPatch,
    db: DbSession,
    clock: ClockDep,
    user_settings: SettingsDep,
    objective_map: ObjectiveMap,
) -> CardView:
    return await card_service.update_card(
        db,
        card_id=card_id,
        patch=patch,
        settings=user_settings,
        now=clock.now(),
        objective_map=objective_map,
    )


@router.delete("/cards/{card_id}", response_model=OkResponse)
async def delete_card(card_id: int, db: DbSession) -> OkResponse:
    await card_service.delete_card(db, card_id=card_id)
    return OkResponse()
