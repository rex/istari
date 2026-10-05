"""`/api/progress`."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.contracts.progress import ProgressView
from app.deps import ActiveExam, ClockDep, DbSession, ObjectiveMap, SettingsDep, require_auth
from app.services.progress import build_progress

router = APIRouter(dependencies=[Depends(require_auth)])


@router.get("/progress", response_model=ProgressView)
async def progress(
    db: DbSession,
    clock: ClockDep,
    user_settings: SettingsDep,
    exam: ActiveExam,
    objective_map: ObjectiveMap,
) -> ProgressView:
    return await build_progress(
        db, settings=user_settings, exam=exam, now=clock.now(), objective_map=objective_map
    )
