"""Subject → certification → exam version → domain → objective."""

from __future__ import annotations

from datetime import date

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.adapters.db.base import Base, JsonList


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(200))


class Certification(Base):
    __tablename__ = "certifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="RESTRICT"))
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    provider: Mapped[str] = mapped_column(String(100))


class ExamVersion(Base):
    __tablename__ = "exam_versions"
    __table_args__ = (UniqueConstraint("certification_id", "code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    certification_id: Mapped[int] = mapped_column(
        ForeignKey("certifications.id", ondelete="RESTRICT")
    )
    code: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(200))
    guide_revision: Mapped[str | None] = mapped_column(String(100), default=None)
    duration_minutes: Mapped[int] = mapped_column(Integer)
    scored_questions: Mapped[int] = mapped_column(Integer)
    unscored_questions: Mapped[int] = mapped_column(Integer)
    passing_scaled_score: Mapped[int] = mapped_column(Integer)
    score_scale_min: Mapped[int] = mapped_column(Integer)
    score_scale_max: Mapped[int] = mapped_column(Integer)
    format_notes: Mapped[str] = mapped_column(Text, default="")
    # verified | unverified — never inferred, always stated by the pack author.
    verification_status: Mapped[str] = mapped_column(String(16), default="unverified")
    checked_on: Mapped[date | None] = mapped_column(default=None)
    sources: Mapped[JsonList] = mapped_column(default=list)

    domains: Mapped[list[Domain]] = relationship(
        back_populates="exam_version", order_by="Domain.position", lazy="raise"
    )


class Domain(Base):
    __tablename__ = "domains"
    __table_args__ = (UniqueConstraint("exam_version_id", "code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    exam_version_id: Mapped[int] = mapped_column(ForeignKey("exam_versions.id", ondelete="CASCADE"))
    code: Mapped[str] = mapped_column(String(16))
    name: Mapped[str] = mapped_column(String(200))
    weight_percent: Mapped[int] = mapped_column(Integer)
    position: Mapped[int] = mapped_column(Integer)

    exam_version: Mapped[ExamVersion] = relationship(back_populates="domains", lazy="raise")
    objectives: Mapped[list[Objective]] = relationship(
        back_populates="domain", order_by="Objective.position", lazy="raise"
    )


class Objective(Base):
    __tablename__ = "objectives"
    __table_args__ = (UniqueConstraint("domain_id", "code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    domain_id: Mapped[int] = mapped_column(ForeignKey("domains.id", ondelete="CASCADE"))
    code: Mapped[str] = mapped_column(String(16))
    title: Mapped[str] = mapped_column(String(300))
    knowledge: Mapped[list[str]] = mapped_column(default=list)
    skills: Mapped[list[str]] = mapped_column(default=list)
    position: Mapped[int] = mapped_column(Integer)

    domain: Mapped[Domain] = relationship(back_populates="objectives", lazy="raise")
