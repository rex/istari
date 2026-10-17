"""Figures: the drawing itself for the figure endpoint, and the views a lesson embeds."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import (
    ContentItem,
    ContentItemObjective,
    ContentRevision,
    Domain,
    Objective,
)
from app.contracts.common import ObjectiveRef
from app.contracts.figure import FigureView
from app.domain.exceptions import NotFoundError
from app.services.content_query import (
    USABLE_REVIEW_STATUSES,
    content_str,
    get_item,
    objective_codes_for_items,
    objective_refs,
)
from app.services.lecture_mapping import lecture_mappings


def figure_url(key: str) -> str:
    return f"/api/figures/{key}.svg"


async def figure_svg(db: AsyncSession, key: str) -> str:
    """The current revision's drawing. A retired figure still serves: a lesson may show it."""
    _item, rev = await get_item(db, key, kind="figure")
    return content_str(rev, "svg")


async def figure_views(
    db: AsyncSession, keys: Sequence[str], objective_map: dict[str, ObjectiveRef]
) -> list[FigureView]:
    """The figures a lesson names, in its order. A key no pack has shipped is left out
    rather than breaking the lesson."""
    views: list[FigureView] = []
    for key in keys:
        try:
            item, rev = await get_item(db, key, kind="figure")
        except NotFoundError:
            continue
        codes = (await objective_codes_for_items(db, [item.id])).get(item.id, [])
        views.append(_view(item, rev, codes, objective_map))
    return views


def _view(
    item: ContentItem,
    rev: ContentRevision,
    codes: list[str],
    objective_map: dict[str, ObjectiveRef],
) -> FigureView:
    return FigureView(
        key=item.item_key,
        title=content_str(rev, "title"),
        caption_md=content_str(rev, "caption_md"),
        alt=content_str(rev, "alt"),
        url=figure_url(item.item_key),
        objectives=objective_refs(codes, objective_map),
    )


async def figures_for_objectives(
    db: AsyncSession,
    exam_version_id: int,
    codes: Sequence[str],
    objective_map: dict[str, ObjectiveRef],
) -> list[FigureView]:
    """The usable figures mapped to any of `codes`, each once, in the order of the first
    code they serve. A figure attaches to objectives only, so this is how a lecture, or
    anything else mapped to objectives, borrows the pack's drawings."""
    if not codes:
        return []
    rows = await db.execute(
        select(ContentItem, ContentRevision, Objective.code)
        .join(
            ContentRevision,
            (ContentRevision.item_id == ContentItem.id) & ContentRevision.is_current.is_(True),
        )
        .join(ContentItemObjective, ContentItemObjective.item_id == ContentItem.id)
        .join(Objective, Objective.id == ContentItemObjective.objective_id)
        .join(Domain, Domain.id == Objective.domain_id)
        .where(
            ContentItem.kind == "figure",
            ContentItem.status == "active",
            Domain.exam_version_id == exam_version_id,
            Objective.code.in_(list(codes)),
            ContentRevision.review_status.in_(USABLE_REVIEW_STATUSES)
            | ContentItem.user_approved.is_(True),
        )
    )
    rank = {code: index for index, code in enumerate(codes)}
    best: dict[str, tuple[int, ContentItem, ContentRevision]] = {}
    for item, rev, code in rows.all():
        place = rank.get(code, len(rank))
        if item.item_key not in best or place < best[item.item_key][0]:
            best[item.item_key] = (place, item, rev)
    ordered = sorted(best.values(), key=lambda entry: (entry[0], entry[1].item_key))
    codes_by_item = await objective_codes_for_items(db, [item.id for _, item, _ in ordered])
    return [
        _view(item, rev, codes_by_item.get(item.id, []), objective_map) for _, item, rev in ordered
    ]


async def lecture_figures(
    db: AsyncSession,
    exam_version_id: int,
    key: tuple[str, str],
    objective_map: dict[str, ObjectiveRef],
) -> list[FigureView]:
    """The figures of the objectives a lecture is mapped to: pinned and ruled mappings
    first, then by strength; excluded mappings bring nothing."""
    mappings = await lecture_mappings(db, exam_version_id, key)
    codes = [m.objective_code for m in mappings if m.source != "excluded"]
    return await figures_for_objectives(db, exam_version_id, codes, objective_map)
