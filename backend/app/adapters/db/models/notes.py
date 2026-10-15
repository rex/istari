"""Personal data attached to content: reading progress, notes, lab evidence."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.db.base import Base, TimestampMixin


class ItemProgress(TimestampMixin, Base):
    """Per-item coverage state. Completion is coverage, never evidence of mastery."""

    __tablename__ = "item_progress"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(
        ForeignKey("content_items.id", ondelete="CASCADE"), unique=True
    )
    # 0.0 to 1.0 reading position within the item body.
    position: Mapped[float] = mapped_column(Float, default=0.0)
    bookmarked: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(default=None)
    last_opened_at: Mapped[datetime | None] = mapped_column(default=None)


class Note(TimestampMixin, Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int | None] = mapped_column(
        ForeignKey("content_items.id", ondelete="SET NULL"), default=None, index=True
    )
    body_md: Mapped[str] = mapped_column(Text)


class LabEvidence(TimestampMixin, Base):
    """What the user observed while doing a lab brief by hand. Free text."""

    __tablename__ = "lab_evidence"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(
        ForeignKey("content_items.id", ondelete="CASCADE"), index=True
    )
    body_md: Mapped[str] = mapped_column(Text)


class LabAttempt(Base):
    """One run of a verified lab: set up on the backend, then graded by it.

    `passed` stays NULL until the check has run. A check without a prior setup still
    records an attempt (the grader decides); a transport failure records nothing.
    """

    __tablename__ = "lab_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(
        ForeignKey("content_items.id", ondelete="CASCADE"), index=True
    )
    backend: Mapped[str] = mapped_column(String(16))
    profile: Mapped[str] = mapped_column(String(64))
    question_id: Mapped[str] = mapped_column(String(100))
    k16s_session_id: Mapped[str | None] = mapped_column(String(64), default=None)
    setup_at: Mapped[datetime | None] = mapped_column(default=None)
    checked_at: Mapped[datetime | None] = mapped_column(default=None, index=True)
    passed: Mapped[bool | None] = mapped_column(Boolean, default=None)
    # The grader's text, capped at 16 KB; its last line is the reason shown to the owner.
    output: Mapped[str] = mapped_column(Text, default="")
    # Setup to check, when both happened in this attempt.
    duration_seconds: Mapped[int | None] = mapped_column(Integer, default=None)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
