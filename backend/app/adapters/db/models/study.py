"""Study sessions, the items shown in them, and immutable answers."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.adapters.db.base import Base, JsonDict


class StudySession(Base):
    __tablename__ = "study_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    exam_version_id: Mapped[int] = mapped_column(
        ForeignKey("exam_versions.id", ondelete="RESTRICT")
    )
    # practice (feedback after each answer) | assessment (feedback after completion)
    kind: Mapped[str] = mapped_column(String(16))
    # mixed | weak | new | objective:<code>
    focus: Mapped[str] = mapped_column(String(64))
    planned_minutes: Mapped[int] = mapped_column(Integer)
    # in_progress | completed | abandoned
    status: Mapped[str] = mapped_column(String(16), default="in_progress", index=True)
    # Optimistic-concurrency counter: bumped on every draft save / answer.
    version: Mapped[int] = mapped_column(Integer, default=1)
    explanation: Mapped[JsonDict] = mapped_column(default=dict)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    last_activity_at: Mapped[datetime] = mapped_column(server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(default=None)

    items: Mapped[list[SessionItem]] = relationship(
        back_populates="session", order_by="SessionItem.position", lazy="raise"
    )


class SessionItem(Base):
    __tablename__ = "session_items"
    __table_args__ = (
        UniqueConstraint("session_id", "position"),
        UniqueConstraint("session_id", "item_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("study_sessions.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int] = mapped_column(Integer)
    item_id: Mapped[int] = mapped_column(ForeignKey("content_items.id", ondelete="RESTRICT"))
    revision_id: Mapped[int] = mapped_column(
        ForeignKey("content_revisions.id", ondelete="RESTRICT")
    )
    # The shuffled option ids as shown to the user — stable for the session.
    option_order: Mapped[list[str]] = mapped_column(default=list)
    # pending | answered
    state: Mapped[str] = mapped_column(String(16), default="pending")
    draft_selection: Mapped[list[str] | None] = mapped_column(default=None)
    draft_confidence: Mapped[str | None] = mapped_column(String(16), default=None)

    session: Mapped[StudySession] = relationship(back_populates="items", lazy="raise")
    answer: Mapped[Answer | None] = relationship(back_populates="session_item", lazy="raise")


class Answer(Base):
    """Immutable attempt. One per session item; `client_request_id` dedupes retries."""

    __tablename__ = "answers"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_item_id: Mapped[int] = mapped_column(
        ForeignKey("session_items.id", ondelete="CASCADE"), unique=True
    )
    session_id: Mapped[int] = mapped_column(
        ForeignKey("study_sessions.id", ondelete="CASCADE"), index=True
    )
    item_id: Mapped[int] = mapped_column(
        ForeignKey("content_items.id", ondelete="RESTRICT"), index=True
    )
    revision_id: Mapped[int] = mapped_column(
        ForeignKey("content_revisions.id", ondelete="RESTRICT")
    )
    family_key: Mapped[str] = mapped_column(String(100), index=True)
    session_kind: Mapped[str] = mapped_column(String(16))
    selected_option_ids: Mapped[list[str]] = mapped_column(default=list)
    is_correct: Mapped[bool] = mapped_column(Boolean)
    # guessing | uncertain | confident | null
    confidence: Mapped[str | None] = mapped_column(String(16), default=None)
    first_attempt: Mapped[bool] = mapped_column(Boolean)
    client_request_id: Mapped[str | None] = mapped_column(String(64), unique=True, default=None)
    answered_at: Mapped[datetime] = mapped_column(server_default=func.now(), index=True)

    session_item: Mapped[SessionItem] = relationship(back_populates="answer", lazy="raise")
