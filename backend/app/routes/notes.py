"""Personal notes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from app.contracts.common import OkResponse
from app.contracts.lesson import NoteCreate, NotePatch, NoteView
from app.deps import DbSession, require_auth
from app.services import notes as note_service

router = APIRouter(dependencies=[Depends(require_auth)])


@router.get("", response_model=list[NoteView])
async def list_notes(db: DbSession, item_key: str | None = Query(default=None)) -> list[NoteView]:
    return await note_service.list_notes(db, item_key=item_key)


@router.post("", response_model=NoteView, status_code=status.HTTP_201_CREATED)
async def create(req: NoteCreate, db: DbSession) -> NoteView:
    return await note_service.create_note(db, req)


@router.patch("/{note_id}", response_model=NoteView)
async def update(note_id: int, patch: NotePatch, db: DbSession) -> NoteView:
    return await note_service.update_note(db, note_id, patch)


@router.delete("/{note_id}", response_model=OkResponse)
async def delete(note_id: int, db: DbSession) -> OkResponse:
    await note_service.delete_note(db, note_id)
    return OkResponse()
