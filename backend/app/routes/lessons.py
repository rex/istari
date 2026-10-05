"""Lessons and reading progress."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.contracts.lesson import ItemProgressView, LessonProgressPatch, LessonSummary, LessonView
from app.deps import ActiveExam, ClockDep, DbSession, ObjectiveMap, SettingsDep, require_auth
from app.services import lessons as lesson_service

router = APIRouter(dependencies=[Depends(require_auth)])


@router.get("", response_model=list[LessonSummary])
async def list_all(
    db: DbSession, exam: ActiveExam, user_settings: SettingsDep, objective_map: ObjectiveMap
) -> list[LessonSummary]:
    return await lesson_service.list_lessons(
        db, exam_version_id=exam.id, settings=user_settings, objective_map=objective_map
    )


@router.get("/{key}", response_model=LessonView)
async def read(
    key: str,
    db: DbSession,
    clock: ClockDep,
    user_settings: SettingsDep,
    objective_map: ObjectiveMap,
) -> LessonView:
    return await lesson_service.get_lesson(
        db, key=key, settings=user_settings, objective_map=objective_map, now=clock.now()
    )


@router.patch("/{key}/progress", response_model=ItemProgressView)
async def progress(
    key: str, patch: LessonProgressPatch, db: DbSession, clock: ClockDep
) -> ItemProgressView:
    return await lesson_service.update_progress(db, key=key, patch=patch, now=clock.now())
