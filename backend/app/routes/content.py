"""Content administration. Behind auth like everything else; kept out of the main nav."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from app.adapters.db.models import ContentPack
from app.contracts.content import (
    ContentItemDetail,
    ContentItemFlags,
    ContentItemUpdate,
    ContentListResponse,
    ImportReportView,
    ImportRequest,
)
from app.deps import ActiveExam, ClockDep, DbSession, require_auth
from app.domain.content.validate import parse_pack
from app.services import content_admin
from app.services.content_export import export_pack
from app.services.content_import import import_pack

router = APIRouter(dependencies=[Depends(require_auth)])


@router.get("/items", response_model=ContentListResponse)
async def list_items(
    db: DbSession,
    exam: ActiveExam,
    kind: str | None = Query(default=None),
    status: str | None = Query(default=None),
) -> ContentListResponse:
    return await content_admin.list_content(db, exam_version_id=exam.id, kind=kind, status=status)


@router.get("/items/{key}", response_model=ContentItemDetail)
async def item(key: str, db: DbSession) -> ContentItemDetail:
    return await content_admin.item_detail(db, key)


@router.put("/items/{key}", response_model=ContentItemDetail)
async def update_item(
    key: str, req: ContentItemUpdate, db: DbSession, clock: ClockDep
) -> ContentItemDetail:
    return await content_admin.update_item(db, key=key, req=req, now=clock.now())


@router.patch("/items/{key}/flags", response_model=ContentItemDetail)
async def flags(key: str, req: ContentItemFlags, db: DbSession) -> ContentItemDetail:
    return await content_admin.set_flags(db, key=key, flags=req)


@router.post("/import", response_model=ImportReportView)
async def import_json(req: ImportRequest, db: DbSession, clock: ClockDep) -> ImportReportView:
    spec = parse_pack(req.pack)
    report = await import_pack(db, spec, dry_run=req.dry_run, now=clock.now())
    return ImportReportView(
        pack_slug=report.pack_slug,
        dry_run=report.dry_run,
        created=report.created,
        updated=report.updated,
        unchanged=report.unchanged,
        retired=report.retired,
        track_changes=report.track_changes,
        warnings=report.warnings,
        counts=report.counts(),
    )


@router.get("/packs", response_model=list[dict[str, object]])
async def packs(db: DbSession) -> list[dict[str, object]]:
    rows = (await db.scalars(select(ContentPack).order_by(ContentPack.slug))).all()
    return [
        {
            "slug": p.slug,
            "name": p.name,
            "version": p.version,
            "authored_by": p.authored_by,
            "imported_at": p.imported_at.isoformat(),
            "manifest": p.manifest,
        }
        for p in rows
    ]


@router.get("/export/{slug}", response_model=dict[str, object])
async def export_json(slug: str, db: DbSession) -> dict[str, object]:
    spec = await export_pack(db, slug)
    return spec.model_dump(mode="json")
