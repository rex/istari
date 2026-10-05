"""Exam versions (tracks)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.contracts.track import TrackSummary, TrackView
from app.deps import ActiveExam, DbSession, require_auth
from app.services.track import list_tracks, track_view

router = APIRouter(dependencies=[Depends(require_auth)])


@router.get("/tracks", response_model=list[TrackSummary])
async def tracks(db: DbSession) -> list[TrackSummary]:
    return await list_tracks(db)


@router.get("/tracks/{exam_version_id}", response_model=TrackView)
async def track_by_id(exam_version_id: int, db: DbSession) -> TrackView:
    return await track_view(db, exam_version_id)


@router.get("/track", response_model=TrackView)
async def active(db: DbSession, exam: ActiveExam) -> TrackView:
    return await track_view(db, exam.id)
