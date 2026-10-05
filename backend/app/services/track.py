"""Exam-version (track) lookups and views."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.adapters.db.models import Certification, Domain, ExamVersion, UserSettings
from app.contracts.common import SourceView
from app.contracts.track import DomainView, ObjectiveView, TrackSummary, TrackView
from app.domain.exceptions import NotFoundError


def track_summary(exam: ExamVersion, cert: Certification) -> TrackSummary:
    return TrackSummary(
        exam_version_id=exam.id,
        code=exam.code,
        name=exam.name,
        certification=cert.name,
        provider=cert.provider,
        verification_status=exam.verification_status,
        checked_on=exam.checked_on,
    )


async def list_tracks(db: AsyncSession) -> list[TrackSummary]:
    rows = await db.execute(
        select(ExamVersion, Certification)
        .join(Certification, Certification.id == ExamVersion.certification_id)
        .order_by(Certification.name, ExamVersion.code)
    )
    return [track_summary(exam, cert) for exam, cert in rows.all()]


async def get_exam_version(db: AsyncSession, exam_version_id: int) -> ExamVersion:
    exam = await db.get(ExamVersion, exam_version_id)
    if exam is None:
        raise NotFoundError("exam version not found")
    return exam


async def active_track(db: AsyncSession, settings: UserSettings) -> ExamVersion | None:
    if settings.active_exam_version_id is None:
        return None
    return await db.get(ExamVersion, settings.active_exam_version_id)


async def track_view(db: AsyncSession, exam_version_id: int) -> TrackView:
    row = await db.execute(
        select(ExamVersion, Certification)
        .join(Certification, Certification.id == ExamVersion.certification_id)
        .where(ExamVersion.id == exam_version_id)
        .options(selectinload(ExamVersion.domains).selectinload(Domain.objectives))
    )
    pair = row.first()
    if pair is None:
        raise NotFoundError("exam version not found")
    exam, cert = pair
    sources = [SourceView.model_validate(s) for s in exam.sources if isinstance(s, dict)]
    return TrackView(
        **track_summary(exam, cert).model_dump(),
        duration_minutes=exam.duration_minutes,
        scored_questions=exam.scored_questions,
        unscored_questions=exam.unscored_questions,
        passing_scaled_score=exam.passing_scaled_score,
        score_scale=(exam.score_scale_min, exam.score_scale_max),
        format_notes=exam.format_notes,
        guide_revision=exam.guide_revision,
        sources=sources,
        domains=[
            DomainView(
                id=d.id,
                code=d.code,
                name=d.name,
                weight_percent=d.weight_percent,
                objectives=[
                    ObjectiveView(
                        id=o.id,
                        code=o.code,
                        title=o.title,
                        knowledge=list(o.knowledge),
                        skills=list(o.skills),
                    )
                    for o in d.objectives
                ],
            )
            for d in exam.domains
        ],
    )
