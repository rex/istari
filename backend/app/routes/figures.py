"""The figure endpoint: a figure's current drawing, served as an image."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.deps import DbSession, require_auth
from app.services.figures import figure_svg

router = APIRouter(dependencies=[Depends(require_auth)])


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
