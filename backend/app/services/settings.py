"""The single settings row, onboarding, and its API view."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import ExamVersion, UserSettings
from app.contracts.auth import OnboardingRequest, SettingsPatch, SettingsView
from app.domain.exceptions import NotFoundError
from app.domain.timeframes import resolve_timezone


async def get_settings(db: AsyncSession) -> UserSettings:
    """The singleton row, created on first use.

    Two first requests at once (a fresh tab plus a refetch after login) must not race
    into an IntegrityError: the insert runs in a savepoint, and when it loses, the
    winner's row is read instead.
    """
    row = await db.get(UserSettings, 1)
    if row is not None:
        return row
    try:
        async with db.begin_nested():
            db.add(UserSettings(id=1))
            await db.flush()
    except IntegrityError:
        pass  # another transaction inserted it first; it is committed by now
    row = await db.get(UserSettings, 1)
    if row is None:  # pragma: no cover - a losing insert only fails once the winner committed
        raise RuntimeError("user_settings singleton missing after insert")
    return row


def settings_view(row: UserSettings) -> SettingsView:
    return SettingsView(
        timezone=row.timezone,
        preferred_session_minutes=row.preferred_session_minutes,
        exam_date=row.exam_date,
        active_exam_version_id=row.active_exam_version_id,
        daily_review_limit=row.daily_review_limit,
        backlog_mode=row.backlog_mode,
        familiar_objective_codes=list(row.familiar_objective_codes),
        onboarding_completed_at=row.onboarding_completed_at,
    )


async def update_settings(db: AsyncSession, patch: SettingsPatch) -> UserSettings:
    row = await get_settings(db)
    if patch.timezone is not None:
        resolve_timezone(patch.timezone)
        row.timezone = patch.timezone
    if patch.preferred_session_minutes is not None:
        row.preferred_session_minutes = patch.preferred_session_minutes
    if patch.clear_exam_date:
        row.exam_date = None
    elif patch.exam_date is not None:
        row.exam_date = patch.exam_date
    if patch.daily_review_limit is not None:
        row.daily_review_limit = patch.daily_review_limit
    if patch.backlog_mode is not None:
        row.backlog_mode = patch.backlog_mode
    if patch.familiar_objective_codes is not None:
        row.familiar_objective_codes = sorted(set(patch.familiar_objective_codes))
    await db.flush()
    return row


async def complete_onboarding(
    db: AsyncSession, req: OnboardingRequest, *, now: datetime
) -> UserSettings:
    exam = await db.scalar(select(ExamVersion).where(ExamVersion.id == req.exam_version_id))
    if exam is None:
        raise NotFoundError("exam version not found")
    row = await get_settings(db)
    row.active_exam_version_id = exam.id
    row.exam_date = req.exam_date
    row.preferred_session_minutes = req.preferred_session_minutes
    row.familiar_objective_codes = sorted(set(req.familiar_objective_codes))
    row.onboarding_completed_at = now
    await db.flush()
    return row
