"""`/api/health` — liveness + readiness (database reachable). No auth."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.buildinfo import BuildInfo
from app.contracts.health import HealthStatus, HealthView, VerifierHealth
from app.deps import DbSession
from app.services.verifier_clients import VerifierClient

router = APIRouter()


def _verifier_health(client: VerifierClient | None) -> VerifierHealth:
    """What the last background poll saw. Reading it costs nothing, by design."""
    if client is None:
        return VerifierHealth(configured=False)
    snapshot = client.snapshot
    if snapshot is None:
        return VerifierHealth(configured=True)
    status = snapshot.status
    return VerifierHealth(
        configured=True,
        reachable=snapshot.reachable,
        mode=status.mode if status else None,
        profiles=list(status.profiles) if status else [],
        checked_at=snapshot.checked_at.isoformat(),
    )


def _view(
    info: BuildInfo, status: HealthStatus, reason: str | None, request: Request
) -> HealthView:
    return HealthView(
        status=status,
        reason=reason,
        version=info.version,
        commit=info.commit,
        built_at=info.built_at,
        started_at=info.started_at.isoformat(),
        k16s=_verifier_health(request.app.state.k16s),
        localemu=_verifier_health(request.app.state.localemu),
    )


@router.get("/health", response_model=HealthView)
async def health(request: Request, db: DbSession) -> JSONResponse:
    info: BuildInfo = request.app.state.build_info
    try:
        await asyncio.wait_for(db.execute(text("SELECT 1")), timeout=0.75)
    except (TimeoutError, OSError, Exception):
        body = _view(info, "unhealthy", "db", request)
        return JSONResponse(status_code=503, content=body.model_dump())
    return JSONResponse(content=_view(info, "ok", None, request).model_dump())
