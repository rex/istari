"""Figures: the drawing itself for the figure endpoint, and the views a lesson embeds."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.common import ObjectiveRef
from app.contracts.figure import FigureView
from app.domain.exceptions import NotFoundError
from app.services.content_query import (
    content_str,
    get_item,
    objective_codes_for_items,
    objective_refs,
)


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
        views.append(
            FigureView(
                key=key,
                title=content_str(rev, "title"),
                caption_md=content_str(rev, "caption_md"),
                alt=content_str(rev, "alt"),
                url=figure_url(key),
                objectives=objective_refs(codes, objective_map),
            )
        )
    return views
