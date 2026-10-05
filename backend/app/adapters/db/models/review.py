"""Spaced-repetition cards, scheduler configuration and the review-event ledger."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.db.base import Base, TimestampMixin


class SchedulerConfig(Base):
    """A frozen scheduler configuration; every card and event points at one."""

    __tablename__ = "scheduler_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)
    library: Mapped[str] = mapped_column(String(32))
    library_version: Mapped[str] = mapped_column(String(32))
    parameters: Mapped[list[float]] = mapped_column(default=list)
    desired_retention: Mapped[float] = mapped_column(Float)
    learning_steps_seconds: Mapped[list[int]] = mapped_column(default=list)
    relearning_steps_seconds: Mapped[list[int]] = mapped_column(default=list)
    maximum_interval: Mapped[int] = mapped_column(Integer)
    enable_fuzzing: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class ReviewCard(TimestampMixin, Base):
    __tablename__ = "review_cards"
    __table_args__ = (
        Index(
            "uq_review_cards_source_item",
            "source_kind",
            "source_item_id",
            unique=True,
            postgresql_where=text("source_item_id IS NOT NULL"),
        ),
        Index(
            "uq_review_cards_source_note",
            "source_note_id",
            unique=True,
            postgresql_where=text("source_note_id IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # flashcard | mistake | note
    source_kind: Mapped[str] = mapped_column(String(16))
    source_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("content_items.id", ondelete="SET NULL"), default=None
    )
    source_note_id: Mapped[int | None] = mapped_column(
        ForeignKey("notes.id", ondelete="SET NULL"), default=None
    )
    front_md: Mapped[str] = mapped_column(Text)
    back_md: Mapped[str] = mapped_column(Text)
    user_edited: Mapped[bool] = mapped_column(Boolean, default=False)
    suspended: Mapped[bool] = mapped_column(Boolean, default=False)

    # FSRS state (py-fsrs Card fields); `due` and `last_review` are UTC.
    state: Mapped[int] = mapped_column(Integer)
    step: Mapped[int | None] = mapped_column(Integer, default=None)
    stability: Mapped[float | None] = mapped_column(Float, default=None)
    difficulty: Mapped[float | None] = mapped_column(Float, default=None)
    due: Mapped[datetime] = mapped_column(index=True)
    last_review: Mapped[datetime | None] = mapped_column(default=None)
    scheduler_config_id: Mapped[int] = mapped_column(
        ForeignKey("scheduler_configs.id", ondelete="RESTRICT")
    )
    scheduler_version: Mapped[str] = mapped_column(String(64))


class ReviewEvent(Base):
    """Append-only: what was rated, when, and what the scheduler decided."""

    __tablename__ = "review_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    card_id: Mapped[int] = mapped_column(
        ForeignKey("review_cards.id", ondelete="CASCADE"), index=True
    )
    rating: Mapped[int] = mapped_column(Integer)
    reviewed_at: Mapped[datetime] = mapped_column(index=True)
    review_duration_ms: Mapped[int | None] = mapped_column(Integer, default=None)
    due_before: Mapped[datetime]
    due_after: Mapped[datetime]
    state_before: Mapped[int] = mapped_column(Integer)
    state_after: Mapped[int] = mapped_column(Integer)
    stability_after: Mapped[float | None] = mapped_column(Float, default=None)
    difficulty_after: Mapped[float | None] = mapped_column(Float, default=None)
    scheduler_config_id: Mapped[int] = mapped_column(
        ForeignKey("scheduler_configs.id", ondelete="RESTRICT")
    )
    scheduler_version: Mapped[str] = mapped_column(String(64))
    client_request_id: Mapped[str | None] = mapped_column(String(64), unique=True, default=None)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
