"""User settings — exactly one row (id = 1)."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.db.base import Base, TimestampMixin


class UserSettings(TimestampMixin, Base):
    __tablename__ = "user_settings"
    __table_args__ = (CheckConstraint("id = 1", name="singleton"),)

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    timezone: Mapped[str] = mapped_column(String(64), default="America/Chicago")
    preferred_session_minutes: Mapped[int] = mapped_column(Integer, default=15)
    exam_date: Mapped[date | None] = mapped_column(default=None)
    active_exam_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("exam_versions.id", ondelete="SET NULL"), default=None
    )
    daily_review_limit: Mapped[int] = mapped_column(Integer, default=50)
    # normal | recovery — recovery caps the visible backlog and surfaces the
    # oldest cards first, without resetting anything.
    backlog_mode: Mapped[str] = mapped_column(String(16), default="normal")
    # Objectives the user declared familiar at onboarding. Deprioritises lessons;
    # never counts as demonstrated mastery.
    familiar_objective_codes: Mapped[list[str]] = mapped_column(default=list)
    onboarding_completed_at: Mapped[datetime | None] = mapped_column(default=None)
