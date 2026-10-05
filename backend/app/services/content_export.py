"""Export a pack from the database in the same JSON shape the importer accepts."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.adapters.db.models import (
    Certification,
    ContentItem,
    ContentPack,
    ContentRevision,
    Domain,
    ExamVersion,
    Subject,
)
from app.domain.content.schemas.pack import ContentPackSpec
from app.domain.content.validate import parse_pack
from app.domain.exceptions import NotFoundError

_PLURAL = {"lesson": "lessons", "question": "questions", "flashcard": "flashcards", "lab": "labs"}


async def export_pack(db: AsyncSession, slug: str) -> ContentPackSpec:
    pack = await db.scalar(select(ContentPack).where(ContentPack.slug == slug))
    if pack is None:
        raise NotFoundError(f"pack '{slug}' not found")
    exam = await db.scalar(
        select(ExamVersion)
        .where(ExamVersion.id == pack.exam_version_id)
        .options(selectinload(ExamVersion.domains).selectinload(Domain.objectives))
    )
    if exam is None:
        raise NotFoundError("exam version not found")
    cert = await db.get(Certification, exam.certification_id)
    subject = await db.get(Subject, cert.subject_id) if cert else None
    if cert is None or subject is None:
        raise NotFoundError("certification not found")

    rows = await db.execute(
        select(ContentItem, ContentRevision)
        .join(ContentRevision, ContentRevision.item_id == ContentItem.id)
        .where(
            ContentItem.pack_id == pack.id,
            ContentItem.status != "retired",
            ContentRevision.is_current.is_(True),
        )
        .order_by(ContentItem.kind, ContentItem.item_key)
    )
    items: dict[str, list[dict[str, object]]] = {v: [] for v in _PLURAL.values()}
    for item, rev in rows.all():
        body: dict[str, object] = {
            "slug": item.item_key,
            "objectives": list(rev.objective_codes),
            "sources": list(rev.sources),
            "provenance": dict(rev.provenance),
            "review_status": rev.review_status,
            **rev.content,
        }
        if item.kind == "question" and item.family_key != item.item_key:
            body["family"] = item.family_key
        items[_PLURAL[item.kind]].append(body)

    manifest = pack.manifest
    data: dict[str, object] = {
        "schema_version": 1,
        "pack": {
            "slug": pack.slug,
            "name": pack.name,
            "version": pack.version,
            "description": pack.notes,
            "authored_by": pack.authored_by,
            "coverage_notes_md": str(manifest.get("coverage_notes_md", "")),
        },
        "subject": {"slug": subject.slug, "name": subject.name},
        "certification": {"slug": cert.slug, "name": cert.name, "provider": cert.provider},
        "exam_version": {
            "code": exam.code,
            "name": exam.name,
            "guide_revision": exam.guide_revision,
            "duration_minutes": exam.duration_minutes,
            "scored_questions": exam.scored_questions,
            "unscored_questions": exam.unscored_questions,
            "passing_scaled_score": exam.passing_scaled_score,
            "score_scale": [exam.score_scale_min, exam.score_scale_max],
            "format_notes": exam.format_notes,
            "verification": {
                "status": exam.verification_status,
                "checked_on": exam.checked_on.isoformat() if exam.checked_on else None,
                "sources": list(exam.sources),
            },
        },
        "domains": [
            {
                "code": d.code,
                "name": d.name,
                "weight_percent": d.weight_percent,
                "objectives": [
                    {
                        "code": o.code,
                        "title": o.title,
                        "knowledge": list(o.knowledge),
                        "skills": list(o.skills),
                    }
                    for o in d.objectives
                ],
            }
            for d in exam.domains
        ],
        **items,
    }
    # Round-trip through the schema so an export is always a valid import.
    return parse_pack(data)
