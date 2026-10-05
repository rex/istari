"""`/api/today` — what should I do next?"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.contracts.today import TodayView
from app.deps import ActiveExam, ClockDep, DbSession, ObjectiveMap, SettingsDep, require_auth
from app.domain.exceptions import ValidationError
from app.domain.recommendation import BUDGETS
from app.services.today import build_today

router = APIRouter(dependencies=[Depends(require_auth)])


@router.get("/today", response_model=TodayView)
async def today_view(
    db: DbSession,
    clock: ClockDep,
    user_settings: SettingsDep,
    exam: ActiveExam,
    objective_map: ObjectiveMap,
    minutes: int | None = Query(default=None, ge=1, le=120),
) -> TodayView:
    if minutes is not None and minutes not in BUDGETS:
        raise ValidationError(
            "minutes must be one of the session lengths", details={"allowed": sorted(BUDGETS)}
        )
    return await build_today(
        db,
        settings=user_settings,
        exam=exam,
        now=clock.now(),
        minutes=minutes or user_settings.preferred_session_minutes,
        objective_map=objective_map,
    )
