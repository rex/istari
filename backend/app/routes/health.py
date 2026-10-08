"""`/api/health` — liveness + readiness (database reachable). No auth."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.buildinfo import BuildInfo
from app.contracts.health import HealthStatus, HealthView
from app.deps import DbSession

router = APIRouter()


def _view(info: BuildInfo, status: HealthStatus, reason: str | None) -> HealthView:
    return HealthView(
        status=status,
        reason=reason,
        version=info.version,
        commit=info.commit,
        built_at=info.built_at,
        started_at=info.started_at.isoformat(),
    )


@router.get("/health", response_model=HealthView)
async def health(request: Request, db: DbSession) -> JSONResponse:
    info: BuildInfo = request.app.state.build_info
    try:
        await asyncio.wait_for(db.execute(text("SELECT 1")), timeout=0.75)
    except (TimeoutError, OSError, Exception):
        body = _view(info, "unhealthy", "db")
        return JSONResponse(status_code=503, content=body.model_dump())
    return JSONResponse(content=_view(info, "ok", None).model_dump())
