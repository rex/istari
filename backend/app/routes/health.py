"""`/api/health` — liveness + readiness (database reachable). No auth."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.deps import DbSession

router = APIRouter()


@router.get("/health")
async def health(db: DbSession) -> JSONResponse:
    try:
        await asyncio.wait_for(db.execute(text("SELECT 1")), timeout=0.75)
    except (TimeoutError, OSError, Exception):
        return JSONResponse(status_code=503, content={"status": "unhealthy", "reason": "db"})
    return JSONResponse(content={"status": "ok"})
