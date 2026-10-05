"""Authentication, settings and the `/api/me` bootstrap payload."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import Field

from app.contracts.common import ApiModel
from app.contracts.track import TrackSummary

SessionMinutes = Literal[5, 15, 30]


class LoginRequest(ApiModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=1024)


class UserView(ApiModel):
    username: str
    csrf_token: str


class SettingsView(ApiModel):
    timezone: str
    preferred_session_minutes: int
    exam_date: date | None
    active_exam_version_id: int | None
    daily_review_limit: int
    backlog_mode: str
    familiar_objective_codes: list[str]
    onboarding_completed_at: datetime | None


class SettingsPatch(ApiModel):
    timezone: str | None = None
    preferred_session_minutes: SessionMinutes | None = None
    exam_date: date | None = None
    clear_exam_date: bool = False
    daily_review_limit: int | None = Field(default=None, ge=1, le=500)
    backlog_mode: Literal["normal", "recovery"] | None = None
    familiar_objective_codes: list[str] | None = None


class OnboardingRequest(ApiModel):
    exam_version_id: int
    exam_date: date | None = None
    preferred_session_minutes: SessionMinutes = 15
    familiar_objective_codes: list[str] = Field(default_factory=list)


class MeView(ApiModel):
    user: UserView
    settings: SettingsView
    track: TrackSummary | None
    available_tracks: list[TrackSummary]
    onboarding_required: bool
