"""Settings and the one-screen onboarding."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.contracts.auth import OnboardingRequest, SettingsPatch, SettingsView
from app.deps import ClockDep, DbSession, require_auth
from app.services.settings import complete_onboarding, get_settings, settings_view, update_settings

router = APIRouter(dependencies=[Depends(require_auth)])


@router.get("/settings", response_model=SettingsView)
async def read_settings(db: DbSession) -> SettingsView:
    return settings_view(await get_settings(db))


@router.patch("/settings", response_model=SettingsView)
async def patch_settings(patch: SettingsPatch, db: DbSession) -> SettingsView:
    return settings_view(await update_settings(db, patch))


@router.post("/onboarding", response_model=SettingsView)
async def onboarding(req: OnboardingRequest, db: DbSession, clock: ClockDep) -> SettingsView:
    return settings_view(await complete_onboarding(db, req, now=clock.now()))
