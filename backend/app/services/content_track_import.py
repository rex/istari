"""Upsert subject / certification / exam version / domains / objectives from a pack."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import Certification, Domain, ExamVersion, Objective, Subject
from app.domain.content.schemas.pack import ContentPackSpec

_EXAM_FIELDS = (
    "name",
    "guide_revision",
    "duration_minutes",
    "scored_questions",
    "unscored_questions",
    "passing_scaled_score",
    "format_notes",
)


async def upsert_track(
    db: AsyncSession, spec: ContentPackSpec, notes: list[str]
) -> tuple[ExamVersion, dict[str, Objective]]:
    """Returns the exam version row and a code → Objective map for linking items."""
    subject = await db.scalar(select(Subject).where(Subject.slug == spec.subject.slug))
    if subject is None:
        subject = Subject(slug=spec.subject.slug, name=spec.subject.name)
        db.add(subject)
        await db.flush()
    elif subject.name != spec.subject.name:
        notes.append(f"subject.name: {subject.name!r} -> {spec.subject.name!r}")
        subject.name = spec.subject.name

    cert = await db.scalar(
        select(Certification).where(Certification.slug == spec.certification.slug)
    )
    if cert is None:
        cert = Certification(
            subject_id=subject.id,
            slug=spec.certification.slug,
            name=spec.certification.name,
            provider=spec.certification.provider,
        )
        db.add(cert)
        await db.flush()
    else:
        for field in ("name", "provider"):
            new = getattr(spec.certification, field)
            if getattr(cert, field) != new:
                notes.append(f"certification.{field}: {getattr(cert, field)!r} -> {new!r}")
                setattr(cert, field, new)

    exam = await _upsert_exam(db, cert.id, spec, notes)
    objectives = await _upsert_domains(db, exam, spec, notes)
    await db.flush()
    return exam, objectives


async def _upsert_exam(
    db: AsyncSession, certification_id: int, spec: ContentPackSpec, notes: list[str]
) -> ExamVersion:
    ev = spec.exam_version
    verification = ev.verification
    sources: list[object] = [s.model_dump(mode="json") for s in verification.sources]
    exam = await db.scalar(
        select(ExamVersion).where(
            ExamVersion.certification_id == certification_id, ExamVersion.code == ev.code
        )
    )
    if exam is None:
        exam = ExamVersion(
            certification_id=certification_id,
            code=ev.code,
            name=ev.name,
            guide_revision=ev.guide_revision,
            duration_minutes=ev.duration_minutes,
            scored_questions=ev.scored_questions,
            unscored_questions=ev.unscored_questions,
            passing_scaled_score=ev.passing_scaled_score,
            score_scale_min=ev.score_scale[0],
            score_scale_max=ev.score_scale[1],
            format_notes=ev.format_notes,
            verification_status=verification.status,
            checked_on=verification.checked_on,
            sources=sources,
        )
        db.add(exam)
        await db.flush()
        return exam

    for field in _EXAM_FIELDS:
        new = getattr(ev, field)
        if getattr(exam, field) != new:
            notes.append(f"exam_version.{field}: {getattr(exam, field)!r} -> {new!r}")
            setattr(exam, field, new)
    if (exam.score_scale_min, exam.score_scale_max) != ev.score_scale:
        notes.append("exam_version.score_scale changed")
        exam.score_scale_min, exam.score_scale_max = ev.score_scale
    if (
        exam.verification_status != verification.status
        or exam.checked_on != verification.checked_on
    ):
        notes.append(
            f"exam_version.verification: {exam.verification_status}/{exam.checked_on} -> "
            f"{verification.status}/{verification.checked_on}"
        )
        exam.verification_status = verification.status
        exam.checked_on = verification.checked_on
    exam.sources = sources
    return exam


async def _upsert_domains(
    db: AsyncSession, exam: ExamVersion, spec: ContentPackSpec, notes: list[str]
) -> dict[str, Objective]:
    existing_domains = {
        d.code: d
        for d in (await db.scalars(select(Domain).where(Domain.exam_version_id == exam.id))).all()
    }
    objective_map: dict[str, Objective] = {}
    for position, dspec in enumerate(spec.domains):
        domain = existing_domains.get(dspec.code)
        if domain is None:
            domain = Domain(
                exam_version_id=exam.id,
                code=dspec.code,
                name=dspec.name,
                weight_percent=dspec.weight_percent,
                position=position,
            )
            db.add(domain)
            await db.flush()
        else:
            if domain.weight_percent != dspec.weight_percent:
                notes.append(
                    f"domain {dspec.code} weight: {domain.weight_percent} -> {dspec.weight_percent}"
                )
            domain.name, domain.weight_percent, domain.position = (
                dspec.name,
                dspec.weight_percent,
                position,
            )
        existing_objectives = {
            o.code: o
            for o in (
                await db.scalars(select(Objective).where(Objective.domain_id == domain.id))
            ).all()
        }
        for opos, ospec in enumerate(dspec.objectives):
            objective = existing_objectives.get(ospec.code)
            if objective is None:
                objective = Objective(
                    domain_id=domain.id,
                    code=ospec.code,
                    title=ospec.title,
                    knowledge=list(ospec.knowledge),
                    skills=list(ospec.skills),
                    position=opos,
                )
                db.add(objective)
                await db.flush()
            else:
                if objective.title != ospec.title:
                    notes.append(f"objective {ospec.code} title changed")
                objective.title = ospec.title
                objective.knowledge = list(ospec.knowledge)
                objective.skills = list(ospec.skills)
                objective.position = opos
            objective_map[ospec.code] = objective
        for code in set(existing_objectives) - {o.code for o in dspec.objectives}:
            notes.append(f"objective {code} is not in the pack; kept (items may reference it)")
    for code in set(existing_domains) - {d.code for d in spec.domains}:
        notes.append(f"domain {code} is not in the pack; kept")
    return objective_map
