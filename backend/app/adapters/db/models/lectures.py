"""The lecture-to-objective index: what each lecture on the share says (as term counts),
which objectives it was ranked under for a track, what the owner decided, and the runs."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.db.base import Base, JsonDict, JsonList, TimestampMixin


class IndexedLecture(TimestampMixin, Base):
    """One row per lecture whose captions were read. Term counts, not the transcript: enough
    to re-rank when objectives or lessons change without touching the share again."""

    __tablename__ = "indexed_lectures"
    __table_args__ = (UniqueConstraint("course_slug", "lecture_path"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    course_slug: Mapped[str] = mapped_column(String(120), index=True)
    lecture_path: Mapped[str] = mapped_column(String(1000))
    course_title: Mapped[str] = mapped_column(String(300))
    section_title: Mapped[str] = mapped_column(String(300))
    lecture_title: Mapped[str] = mapped_column(String(300))
    topic: Mapped[str] = mapped_column(String(120))
    exam_code: Mapped[str | None] = mapped_column(String(32), default=None)
    year: Mapped[int | None] = mapped_column(Integer, default=None)
    # From the last caption cue; the player reports the real duration once played.
    duration_seconds: Mapped[float | None] = mapped_column(Float, default=None)
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    excerpt: Mapped[str] = mapped_column(Text, default="")
    terms: Mapped[JsonDict] = mapped_column(default=dict)
    indexed_at: Mapped[datetime] = mapped_column(server_default=func.now())


class LectureObjective(TimestampMixin, Base):
    """A lecture's place under an objective for one track. `rule` and `lexical` rows are
    rewritten by every run; `pinned` and `excluded` rows are the owner's and stay."""

    __tablename__ = "lecture_objectives"
    __table_args__ = (
        UniqueConstraint("exam_version_id", "course_slug", "lecture_path", "objective_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    exam_version_id: Mapped[int] = mapped_column(
        ForeignKey("exam_versions.id", ondelete="CASCADE"), index=True
    )
    course_slug: Mapped[str] = mapped_column(String(120), index=True)
    lecture_path: Mapped[str] = mapped_column(String(1000))
    objective_id: Mapped[int] = mapped_column(
        ForeignKey("objectives.id", ondelete="CASCADE"), index=True
    )
    score: Mapped[float] = mapped_column(Float, default=0.0)
    normalized: Mapped[float] = mapped_column(Float, default=0.0)
    source: Mapped[str] = mapped_column(String(16), index=True)
    matched_terms: Mapped[JsonList] = mapped_column(default=list)


class LectureReview(Base):
    """The owner looked at this lecture's mappings for a track and decided."""

    __tablename__ = "lecture_reviews"
    __table_args__ = (UniqueConstraint("exam_version_id", "course_slug", "lecture_path"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    exam_version_id: Mapped[int] = mapped_column(
        ForeignKey("exam_versions.id", ondelete="CASCADE"), index=True
    )
    course_slug: Mapped[str] = mapped_column(String(120))
    lecture_path: Mapped[str] = mapped_column(String(1000))
    decision: Mapped[str] = mapped_column(String(16))
    reviewed_at: Mapped[datetime] = mapped_column(server_default=func.now())


class LectureIndexRun(Base):
    """One run of the index for a track: what it read and how it ended."""

    __tablename__ = "lecture_index_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    exam_version_id: Mapped[int] = mapped_column(
        ForeignKey("exam_versions.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(16), default="running")
    started_at: Mapped[datetime] = mapped_column(server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(default=None)
    candidate_courses: Mapped[int] = mapped_column(Integer, default=0)
    lectures_total: Mapped[int] = mapped_column(Integer, default=0)
    lectures_with_captions: Mapped[int] = mapped_column(Integer, default=0)
    lectures_indexed: Mapped[int] = mapped_column(Integer, default=0)
    mappings: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, default=None)
