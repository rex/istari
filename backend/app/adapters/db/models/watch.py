"""Where the owner is in each lecture of a course on the learning share."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Float, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.db.base import Base, TimestampMixin


class CourseProgress(TimestampMixin, Base):
    """One row per lecture ever opened. Position is coverage, never evidence of mastery."""

    __tablename__ = "course_progress"
    __table_args__ = (UniqueConstraint("course_slug", "lecture_path"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    course_slug: Mapped[str] = mapped_column(String(120), index=True)
    # Lecture path relative to the course root, as the catalog reports it.
    lecture_path: Mapped[str] = mapped_column(String(1000))
    position_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    duration_seconds: Mapped[float | None] = mapped_column(Float, default=None)
    completed_at: Mapped[datetime | None] = mapped_column(default=None)
    last_watched_at: Mapped[datetime | None] = mapped_column(default=None)
