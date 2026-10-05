"""Personal notes attached to any content item (or free-standing)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import ContentItem, Note
from app.contracts.lesson import NoteCreate, NotePatch, NoteView
from app.domain.exceptions import NotFoundError
from app.services.content_query import get_item
from app.services.lessons import note_view


async def _item_key(db: AsyncSession, item_id: int | None) -> str | None:
    if item_id is None:
        return None
    item = await db.get(ContentItem, item_id)
    return item.item_key if item else None


async def create_note(db: AsyncSession, req: NoteCreate) -> NoteView:
    item_id: int | None = None
    if req.item_key:
        item, _rev = await get_item(db, req.item_key)
        item_id = item.id
    note = Note(item_id=item_id, body_md=req.body_md)
    db.add(note)
    await db.flush()
    await db.refresh(note)
    return note_view(note, req.item_key or None)


async def update_note(db: AsyncSession, note_id: int, patch: NotePatch) -> NoteView:
    note = await db.get(Note, note_id)
    if note is None:
        raise NotFoundError("note not found")
    note.body_md = patch.body_md
    await db.flush()
    await db.refresh(note)
    return note_view(note, await _item_key(db, note.item_id))


async def delete_note(db: AsyncSession, note_id: int) -> None:
    note = await db.get(Note, note_id)
    if note is None:
        raise NotFoundError("note not found")
    await db.delete(note)
    await db.flush()


async def list_notes(db: AsyncSession, *, item_key: str | None) -> list[NoteView]:
    stmt = select(Note).order_by(Note.updated_at.desc())
    if item_key:
        item, _rev = await get_item(db, item_key)
        stmt = stmt.where(Note.item_id == item.id)
    notes = (await db.scalars(stmt.limit(200))).all()
    return [note_view(n, await _item_key(db, n.item_id)) for n in notes]
