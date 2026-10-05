"""Lab briefs and evidence notes. Nothing here touches a cloud account."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import ContentItem, ContentRevision, LabEvidence
from app.contracts.common import ObjectiveRef
from app.contracts.lab import EvidenceCreate, EvidenceView, LabSummary, LabView
from app.domain.exceptions import NotFoundError
from app.services.content_query import (
    content_str,
    get_item,
    list_items,
    objective_codes_for_items,
    objective_refs,
    revision_sources,
)


def _summary(
    item: ContentItem,
    rev: ContentRevision,
    codes: list[str],
    evidence_count: int,
    objective_map: dict[str, ObjectiveRef],
) -> LabSummary:
    minutes = rev.content.get("estimated_minutes", 30)
    return LabSummary(
        item_key=item.item_key,
        title=content_str(rev, "title"),
        estimated_minutes=int(minutes) if isinstance(minutes, int) else 30,
        objectives=objective_refs(codes, objective_map),
        evidence_count=evidence_count,
        review_status=rev.review_status,
    )


def evidence_view(row: LabEvidence) -> EvidenceView:
    return EvidenceView(
        id=row.id, body_md=row.body_md, created_at=row.created_at, updated_at=row.updated_at
    )


async def list_labs(
    db: AsyncSession, *, exam_version_id: int, objective_map: dict[str, ObjectiveRef]
) -> list[LabSummary]:
    rows = await list_items(db, exam_version_id=exam_version_id, kind="lab")
    codes = await objective_codes_for_items(db, (item.id for item, _ in rows))
    counts = dict(
        (
            await db.execute(
                select(LabEvidence.item_id, func.count(LabEvidence.id)).group_by(
                    LabEvidence.item_id
                )
            )
        ).all()
    )
    return [
        _summary(item, rev, codes.get(item.id, []), int(counts.get(item.id, 0)), objective_map)
        for item, rev in rows
    ]


async def get_lab(db: AsyncSession, *, key: str, objective_map: dict[str, ObjectiveRef]) -> LabView:
    item, rev = await get_item(db, key, kind="lab")
    codes = (await objective_codes_for_items(db, [item.id])).get(item.id, [])
    evidence = (
        await db.scalars(
            select(LabEvidence)
            .where(LabEvidence.item_id == item.id)
            .order_by(LabEvidence.created_at)
        )
    ).all()
    summary = _summary(item, rev, codes, len(evidence), objective_map)
    return LabView(
        **summary.model_dump(),
        goals_md=content_str(rev, "goals_md"),
        prerequisites_md=content_str(rev, "prerequisites_md"),
        cost_warning_md=content_str(rev, "cost_warning_md"),
        steps_md=content_str(rev, "steps_md"),
        expected_observations_md=content_str(rev, "expected_observations_md"),
        cleanup_md=content_str(rev, "cleanup_md"),
        sources=revision_sources(rev),
        evidence=[evidence_view(e) for e in evidence],
    )


async def add_evidence(db: AsyncSession, *, key: str, req: EvidenceCreate) -> EvidenceView:
    item, _rev = await get_item(db, key, kind="lab")
    row = LabEvidence(item_id=item.id, body_md=req.body_md)
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return evidence_view(row)


async def update_evidence(
    db: AsyncSession, *, evidence_id: int, req: EvidenceCreate
) -> EvidenceView:
    row = await db.get(LabEvidence, evidence_id)
    if row is None:
        raise NotFoundError("evidence not found")
    row.body_md = req.body_md
    await db.flush()
    await db.refresh(row)
    return evidence_view(row)


async def delete_evidence(db: AsyncSession, *, evidence_id: int) -> None:
    row = await db.get(LabEvidence, evidence_id)
    if row is None:
        raise NotFoundError("evidence not found")
    await db.delete(row)
    await db.flush()
