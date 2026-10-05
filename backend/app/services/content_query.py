"""Read-side helpers shared by every service that touches content."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import (
    ContentItem,
    ContentItemObjective,
    ContentPack,
    ContentRevision,
    Domain,
    Objective,
)
from app.contracts.common import ObjectiveRef, SourceView
from app.domain.exceptions import NotFoundError

ItemRow = tuple[ContentItem, ContentRevision]

# Revisions that may appear in practice/assessment and count toward progress.
USABLE_REVIEW_STATUSES = ("source_checked", "human_reviewed")


async def get_item(db: AsyncSession, key: str, *, kind: str | None = None) -> ItemRow:
    stmt = (
        select(ContentItem, ContentRevision)
        .join(ContentRevision, ContentRevision.item_id == ContentItem.id)
        .where(ContentItem.item_key == key, ContentRevision.is_current.is_(True))
    )
    if kind is not None:
        stmt = stmt.where(ContentItem.kind == kind)
    row = (await db.execute(stmt)).first()
    if row is None:
        raise NotFoundError(f"{kind or 'content item'} '{key}' not found")
    return row[0], row[1]


async def list_items(
    db: AsyncSession,
    *,
    exam_version_id: int,
    kind: str | None = None,
    statuses: Sequence[str] = ("active",),
    usable_only: bool = False,
) -> list[ItemRow]:
    stmt = (
        select(ContentItem, ContentRevision)
        .join(ContentRevision, ContentRevision.item_id == ContentItem.id)
        .join(ContentPack, ContentPack.id == ContentItem.pack_id)
        .where(
            ContentPack.exam_version_id == exam_version_id,
            ContentRevision.is_current.is_(True),
            ContentItem.status.in_(list(statuses)),
        )
        .order_by(ContentItem.kind, ContentItem.item_key)
    )
    if kind is not None:
        stmt = stmt.where(ContentItem.kind == kind)
    if usable_only:
        stmt = stmt.where(
            (ContentRevision.review_status.in_(USABLE_REVIEW_STATUSES))
            | (ContentItem.user_approved.is_(True))
        )
    return [(item, rev) for item, rev in (await db.execute(stmt)).all()]


async def load_objective_map(db: AsyncSession, exam_version_id: int) -> dict[str, ObjectiveRef]:
    rows = await db.execute(
        select(Objective.code, Objective.title, Domain.code)
        .join(Domain, Domain.id == Objective.domain_id)
        .where(Domain.exam_version_id == exam_version_id)
        .order_by(Domain.position, Objective.position)
    )
    return {
        code: ObjectiveRef(code=code, title=title, domain_code=domain_code)
        for code, title, domain_code in rows.all()
    }


async def objective_codes_for_items(
    db: AsyncSession, item_ids: Iterable[int]
) -> dict[int, list[str]]:
    ids = list(item_ids)
    if not ids:
        return {}
    rows = await db.execute(
        select(ContentItemObjective.item_id, Objective.code)
        .join(Objective, Objective.id == ContentItemObjective.objective_id)
        .where(ContentItemObjective.item_id.in_(ids))
        .order_by(Objective.code)
    )
    out: dict[int, list[str]] = defaultdict(list)
    for item_id, code in rows.all():
        out[item_id].append(code)
    return dict(out)


def objective_refs(
    codes: Iterable[str], objective_map: dict[str, ObjectiveRef]
) -> list[ObjectiveRef]:
    refs = []
    for code in codes:
        ref = objective_map.get(code)
        if ref is not None:
            refs.append(ref)
    return refs


def revision_sources(revision: ContentRevision) -> list[SourceView]:
    return [SourceView.model_validate(s) for s in revision.sources if isinstance(s, dict)]


def content_str(revision: ContentRevision, key: str, default: str = "") -> str:
    value = revision.content.get(key, default)
    return value if isinstance(value, str) else default


def content_list(revision: ContentRevision, key: str) -> list[object]:
    value = revision.content.get(key)
    return list(value) if isinstance(value, list) else []
