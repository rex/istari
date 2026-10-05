"""Personal data attached to content: reading progress, notes, lab evidence."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Float, ForeignKey, Text
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
