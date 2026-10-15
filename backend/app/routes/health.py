"""`/api/health` — liveness + readiness (database reachable). No auth."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.adapters.k16s import K16sClient
from app.buildinfo import BuildInfo
from app.contracts.health import HealthStatus, HealthView, K16sHealth
from app.deps import DbSession

router = APIRouter()


def _k16s_health(client: K16sClient | None) -> K16sHealth:
    """What the last background poll saw. Reading it costs nothing, by design."""
    if client is None:
        return K16sHealth(configured=False)
    snapshot = client.snapshot
    if snapshot is None:
        return K16sHealth(configured=True)
    status = snapshot.status
    return K16sHealth(
        configured=True,
        reachable=snapshot.reachable,
        mode=status.mode if status else None,
        profiles=list(status.profiles) if status else [],
        checked_at=snapshot.checked_at.isoformat(),
    )


def _view(
    info: BuildInfo, status: HealthStatus, reason: str | None, k16s: K16sHealth
) -> HealthView:
    return HealthView(
        status=status,
        reason=reason,
        version=info.version,
        commit=info.commit,
        built_at=info.built_at,
        started_at=info.started_at.isoformat(),
        k16s=k16s,
    )


@router.get("/health", response_model=HealthView)
async def health(request: Request, db: DbSession) -> JSONResponse:
    info: BuildInfo = request.app.state.build_info
    k16s = _k16s_health(request.app.state.k16s)
    try:
        await asyncio.wait_for(db.execute(text("SELECT 1")), timeout=0.75)
    except (TimeoutError, OSError, Exception):
        body = _view(info, "unhealthy", "db", k16s)
        return JSONResponse(status_code=503, content=body.model_dump())
    return JSONResponse(content=_view(info, "ok", None, k16s).model_dump())
