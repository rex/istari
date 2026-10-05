"""Content packs, items (stable identity) and immutable revisions."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.adapters.db.base import Base, JsonDict, JsonList, TimestampMixin


class ContentPack(TimestampMixin, Base):
    __tablename__ = "content_packs"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    version: Mapped[str] = mapped_column(String(32))
    exam_version_id: Mapped[int] = mapped_column(
        ForeignKey("exam_versions.id", ondelete="RESTRICT")
    )
    authored_by: Mapped[str] = mapped_column(String(32))
    notes: Mapped[str] = mapped_column(Text, default="")
    manifest: Mapped[JsonDict] = mapped_column(default=dict)
    imported_at: Mapped[datetime] = mapped_column(server_default=func.now())


class ContentItem(TimestampMixin, Base):
    """Stable identity for a lesson, question, flashcard or lab across revisions."""

    __tablename__ = "content_items"
    __table_args__ = (UniqueConstraint("pack_id", "item_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    pack_id: Mapped[int] = mapped_column(ForeignKey("content_packs.id", ondelete="RESTRICT"))
    item_key: Mapped[str] = mapped_column(String(100))
    # lesson | question | flashcard | lab
    kind: Mapped[str] = mapped_column(String(16), index=True)
    # Question family: wording edits keep the family; a genuinely new scenario
    # gets a new family so "unseen" stays honest.
    family_key: Mapped[str] = mapped_column(String(100), index=True)
    # active | retired | invalidated
    status: Mapped[str] = mapped_column(String(16), default="active", index=True)
    user_approved: Mapped[bool] = mapped_column(Boolean, default=False)

    revisions: Mapped[list[ContentRevision]] = relationship(
        back_populates="item", order_by="ContentRevision.revision", lazy="raise"
    )
    objective_links: Mapped[list[ContentItemObjective]] = relationship(
        back_populates="item", lazy="raise", cascade="all, delete-orphan"
    )


class ContentRevision(Base):
    """Immutable snapshot of an item's content. Attempts reference the revision shown."""

    __tablename__ = "content_revisions"
    __table_args__ = (
        UniqueConstraint("item_id", "revision"),
        Index(
            "uq_content_revisions_current",
            "item_id",
            unique=True,
            postgresql_where=text("is_current"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("content_items.id", ondelete="CASCADE"))
    revision: Mapped[int] = mapped_column(Integer)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    content: Mapped[JsonDict] = mapped_column(default=dict)
    objective_codes: Mapped[list[str]] = mapped_column(default=list)
    sources: Mapped[JsonList] = mapped_column(default=list)
    provenance: Mapped[JsonDict] = mapped_column(default=dict)
    # draft | source_checked | human_reviewed
    review_status: Mapped[str] = mapped_column(String(32), default="draft")
    content_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    item: Mapped[ContentItem] = relationship(back_populates="revisions", lazy="raise")


class ContentItemObjective(Base):
    """Current objective mapping for an item (history lives in the revision)."""

    __tablename__ = "content_item_objectives"

    item_id: Mapped[int] = mapped_column(
        ForeignKey("content_items.id", ondelete="CASCADE"), primary_key=True
    )
    objective_id: Mapped[int] = mapped_column(
        ForeignKey("objectives.id", ondelete="CASCADE"), primary_key=True
    )

    item: Mapped[ContentItem] = relationship(back_populates="objective_links", lazy="raise")
