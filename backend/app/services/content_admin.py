"""Content administration: list, inspect, edit (new revision), flag."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import ContentItem, ContentPack, ContentRevision, Objective
from app.contracts.content import (
    ContentItemDetail,
    ContentItemFlags,
    ContentItemSummary,
    ContentItemUpdate,
    ContentListResponse,
)
from app.domain.content.schemas.common import ItemBase
from app.domain.content.schemas.items import FlashcardSpec, LabSpec, LessonSpec, QuestionSpec
from app.domain.content.validate import content_hash
from app.domain.exceptions import ConflictError, NotFoundError, ValidationError
from app.services.content_query import content_str, get_item, list_items

_SPECS: dict[str, type[ItemBase]] = {
    "lesson": LessonSpec,
    "question": QuestionSpec,
    "flashcard": FlashcardSpec,
    "lab": LabSpec,
}


def _preview(item: ContentItem, rev: ContentRevision) -> str:
    key = {"lesson": "title", "question": "stem_md", "flashcard": "front_md", "lab": "title"}[
        item.kind
    ]
    text = content_str(rev, key)
    return text if len(text) <= 140 else text[:137] + "..."


def summary_view(item: ContentItem, rev: ContentRevision) -> ContentItemSummary:
    return ContentItemSummary(
        key=item.item_key,
        kind=item.kind,
        family_key=item.family_key,
        status=item.status,
        user_approved=item.user_approved,
        revision=rev.revision,
        review_status=rev.review_status,
        objectives=list(rev.objective_codes),
        preview=_preview(item, rev),
        updated_at=item.updated_at,
    )


async def list_content(
    db: AsyncSession, *, exam_version_id: int, kind: str | None, status: str | None
) -> ContentListResponse:
    statuses = (status,) if status else ("active", "retired", "invalidated")
    rows = await list_items(db, exam_version_id=exam_version_id, kind=kind, statuses=statuses)
    return ContentListResponse(items=[summary_view(i, r) for i, r in rows], total=len(rows))


async def item_detail(db: AsyncSession, key: str) -> ContentItemDetail:
    item, rev = await get_item(db, key)
    pack = await db.get(ContentPack, item.pack_id)
    revisions = (
        await db.scalars(
            select(ContentRevision.revision)
            .where(ContentRevision.item_id == item.id)
            .order_by(ContentRevision.revision)
        )
    ).all()
    return ContentItemDetail(
        **summary_view(item, rev).model_dump(),
        pack_slug=pack.slug if pack else "?",
        content=dict(rev.content),
        sources=[s for s in rev.sources if isinstance(s, dict)],
        provenance=dict(rev.provenance),
        revisions=[int(r) for r in revisions],
    )


def _validate_item(kind: str, key: str, payload: dict[str, object]) -> ItemBase:
    spec_type = _SPECS.get(kind)
    if spec_type is None:
        raise ValidationError(f"unknown item kind {kind}")
    data = dict(payload)
    data["slug"] = key
    try:
        return spec_type.model_validate(data)
    except ValueError as exc:
        raise ValidationError("item failed schema validation", details={"error": str(exc)}) from exc


async def update_item(
    db: AsyncSession, *, key: str, req: ContentItemUpdate, now: datetime
) -> ContentItemDetail:
    """Validate against the kind's schema and store a new revision; history stays."""
    item, current = await get_item(db, key)
    spec = _validate_item(item.kind, key, req.item)
    digest = content_hash(spec)
    if digest == current.content_hash:
        return await item_detail(db, key)
    pack = await db.get(ContentPack, item.pack_id)
    if pack is None:
        raise NotFoundError("pack not found")
    known = {
        code
        for (code,) in (
            await db.execute(
                select(Objective.code)
                .join(Objective.domain)
                .where(
                    Objective.domain.property.mapper.class_.exam_version_id == pack.exam_version_id
                )
            )
        ).all()
    }
    unknown = [c for c in spec.objectives if c not in known]
    if unknown:
        raise ValidationError("unknown objective codes", details={"codes": unknown})
    current.is_current = False
    await db.flush()
    from app.services.content_import import _add_revision, _sync_objectives

    await _add_revision(db, item, current.revision + 1, spec, digest)
    objectives = {
        o.code: o
        for o in (
            await db.scalars(
                select(Objective)
                .join(Objective.domain)
                .where(
                    Objective.domain.property.mapper.class_.exam_version_id == pack.exam_version_id
                )
            )
        ).all()
    }
    await _sync_objectives(db, item, spec.objectives, objectives)
    if isinstance(spec, QuestionSpec):
        item.family_key = spec.family_key
    item.updated_at = now
    await db.flush()
    return await item_detail(db, key)


async def set_flags(db: AsyncSession, *, key: str, flags: ContentItemFlags) -> ContentItemDetail:
    item, _rev = await get_item(db, key)
    if flags.status is not None:
        item.status = flags.status
    if flags.user_approved is not None:
        item.user_approved = flags.user_approved
    await db.flush()
    return await item_detail(db, key)


async def pack_for_item(db: AsyncSession, key: str) -> ContentPack:
    item, _rev = await get_item(db, key)
    pack = await db.get(ContentPack, item.pack_id)
    if pack is None:
        raise ConflictError("item has no pack")
    return pack
