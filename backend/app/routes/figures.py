"""The figure endpoint: a figure's current drawing, served as an image."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from app.contracts.figure import FigureView
from app.deps import ActiveExam, DbSession, require_auth
from app.services.content_query import load_objective_map
from app.services.figures import figure_svg, lecture_figures

router = APIRouter(dependencies=[Depends(require_auth)])


@router.get("/lecture/{course_slug}", response_model=list[FigureView])
async def figures_for_lecture(
    course_slug: str, db: DbSession, exam: ActiveExam, path: str = Query(min_length=1)
) -> list[FigureView]:
    """The figures of the objectives this lecture is mapped to: the player's "See it" rail."""
    objective_map = await load_objective_map(db, exam.id)
    return await lecture_figures(db, exam.id, (course_slug, path), objective_map)


@router.get("/{key}.svg", response_class=Response)
async def figure(key: str, db: DbSession) -> Response:
    """An SVG loaded through <img> runs nothing; the pack's validation refused scripts and
    external references before it was stored, so the same file is safe opened directly."""
    svg = await figure_svg(db, key)
    return Response(
        content=svg,
        media_type="image/svg+xml",
        headers={"Cache-Control": "private, max-age=3600"},
    )
