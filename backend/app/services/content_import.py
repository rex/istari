"""Import a validated pack: idempotent, revision-aware, never touches user data.

Semantics
- Items are matched by (pack slug, item key). A changed body becomes a new
  revision; the old revision stays (answers reference it). Unchanged bodies
  are no-ops.
- Items present in the database but missing from the pack are *retired*, not
  deleted. Notes, progress, answers, review cards all survive.
- `dry_run=True` runs the whole import inside a savepoint and rolls it back,
  so the preview is exactly what a real import would do.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import (
    ContentItem,
    ContentItemObjective,
    ContentPack,
    ContentRevision,
    Objective,
    ReviewCard,
)
from app.domain.content.schemas.common import ItemBase
from app.domain.content.schemas.items import FlashcardSpec, QuestionSpec
from app.domain.content.schemas.pack import ContentPackSpec
from app.domain.content.validate import content_hash, validate_pack
from app.domain.exceptions import ConflictError, ValidationError
from app.services.content_track_import import upsert_track
from app.services.scheduler_config import build_scheduler, get_default_config

_KINDS: tuple[tuple[str, str], ...] = (
    ("lesson", "lessons"),
    ("question", "questions"),
    ("flashcard", "flashcards"),
    ("lab", "labs"),
)


@dataclass(slots=True)
class ImportReport:
    pack_slug: str
    dry_run: bool
    created: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    retired: list[str] = field(default_factory=list)
    track_changes: list[str] = field(default_factory=list)
    warnings: list[dict[str, object]] = field(default_factory=list)

    def counts(self) -> dict[str, int]:
        return {
            "created": len(self.created),
            "updated": len(self.updated),
            "unchanged": len(self.unchanged),
            "retired": len(self.retired),
        }


def _item_content(item: ItemBase) -> dict[str, object]:
    """Everything except identity/metadata — the body that gets versioned."""
    data = item.model_dump(mode="json")
    for meta in ("key", "objectives", "sources", "provenance", "review_status", "tags"):
        data.pop(meta, None)
    return data


async def import_pack(
    db: AsyncSession, spec: ContentPackSpec, *, dry_run: bool, now: datetime
) -> ImportReport:
    report_validation = validate_pack(spec)
    if not report_validation.ok:
        raise ValidationError(
            "content pack failed cross-reference validation", details=report_validation.as_dict()
        )
    report = ImportReport(pack_slug=spec.pack.slug, dry_run=dry_run)
    report.warnings = [asdict(w) for w in report_validation.warnings]

    savepoint = await db.begin_nested()
    try:
        exam, objectives = await upsert_track(db, spec, report.track_changes)
        pack = await _upsert_pack(db, spec, exam.id, now)
        seen_keys: set[str] = set()
        for kind, attr in _KINDS:
            for item_spec in getattr(spec, attr):
                seen_keys.add(item_spec.key)
                await _import_item(db, pack, kind, item_spec, objectives, report, now)
        await _retire_missing(db, pack, seen_keys, report)
        await db.flush()
    except BaseException:
        await savepoint.rollback()
        raise
    if dry_run:
        await savepoint.rollback()
    else:
        await savepoint.commit()
    return report


async def _upsert_pack(
    db: AsyncSession, spec: ContentPackSpec, exam_version_id: int, now: datetime
) -> ContentPack:
    pack = await db.scalar(select(ContentPack).where(ContentPack.slug == spec.pack.slug))
    manifest: dict[str, object] = {
        "lessons": len(spec.lessons),
        "questions": len(spec.questions),
        "flashcards": len(spec.flashcards),
        "labs": len(spec.labs),
        "coverage_notes_md": spec.pack.coverage_notes_md,
        "description": spec.pack.description,
    }
    if pack is None:
        pack = ContentPack(
            slug=spec.pack.slug,
            name=spec.pack.name,
            version=spec.pack.version,
            exam_version_id=exam_version_id,
            authored_by=spec.pack.authored_by,
            notes=spec.pack.description,
            manifest=manifest,
            imported_at=now,
        )
        db.add(pack)
        await db.flush()
        return pack
    if pack.exam_version_id != exam_version_id:
        raise ConflictError(
            "pack is already bound to a different exam version",
            details={"pack": pack.slug},
        )
    pack.name, pack.version, pack.authored_by = (
        spec.pack.name,
        spec.pack.version,
        spec.pack.authored_by,
    )
    pack.notes, pack.manifest, pack.imported_at = spec.pack.description, manifest, now
    return pack


async def _import_item(
    db: AsyncSession,
    pack: ContentPack,
    kind: str,
    item_spec: ItemBase,
    objectives: dict[str, Objective],
    report: ImportReport,
    now: datetime,
) -> None:
    family_key = item_spec.family_key if isinstance(item_spec, QuestionSpec) else item_spec.key
    digest = content_hash(item_spec)
    item = await db.scalar(
        select(ContentItem).where(
            ContentItem.pack_id == pack.id, ContentItem.item_key == item_spec.key
        )
    )
    if item is None:
        item = ContentItem(
            pack_id=pack.id, item_key=item_spec.key, kind=kind, family_key=family_key
        )
        db.add(item)
        await db.flush()
        await _add_revision(db, item, 1, item_spec, digest)
        report.created.append(item_spec.key)
    else:
        if item.kind != kind:
            raise ConflictError(
                f"item {item_spec.key} changes kind {item.kind} -> {kind}; use a new key"
            )
        current = await db.scalar(
            select(ContentRevision).where(
                ContentRevision.item_id == item.id, ContentRevision.is_current.is_(True)
            )
        )
        item.family_key = family_key
        if item.status == "retired":
            item.status = "active"
        if current is not None and current.content_hash == digest:
            report.unchanged.append(item_spec.key)
        else:
            next_revision = (current.revision + 1) if current is not None else 1
            if current is not None:
                current.is_current = False
                await db.flush()
            await _add_revision(db, item, next_revision, item_spec, digest)
            report.updated.append(item_spec.key)
    await _sync_objectives(db, item, item_spec.objectives, objectives)
    if isinstance(item_spec, FlashcardSpec):
        await _sync_flashcard_card(db, item, item_spec, now)


async def _add_revision(
    db: AsyncSession, item: ContentItem, revision: int, item_spec: ItemBase, digest: str
) -> ContentRevision:
    row = ContentRevision(
        item_id=item.id,
        revision=revision,
        is_current=True,
        content=_item_content(item_spec),
        objective_codes=list(item_spec.objectives),
        sources=[s.model_dump(mode="json") for s in item_spec.sources],
        provenance=item_spec.provenance.model_dump(mode="json"),
        review_status=item_spec.review_status,
        content_hash=digest,
    )
    db.add(row)
    await db.flush()
    return row


async def _sync_objectives(
    db: AsyncSession, item: ContentItem, codes: list[str], objectives: dict[str, Objective]
) -> None:
    wanted = {objectives[code].id for code in codes if code in objectives}
    existing = {
        link.objective_id
        for link in (
            await db.scalars(
                select(ContentItemObjective).where(ContentItemObjective.item_id == item.id)
            )
        ).all()
    }
    for objective_id in wanted - existing:
        db.add(ContentItemObjective(item_id=item.id, objective_id=objective_id))
    for link in (
        await db.scalars(
            select(ContentItemObjective).where(
                ContentItemObjective.item_id == item.id,
                ContentItemObjective.objective_id.in_(list(existing - wanted) or [-1]),
            )
        )
    ).all():
        await db.delete(link)
    await db.flush()


async def _sync_flashcard_card(
    db: AsyncSession, item: ContentItem, spec: FlashcardSpec, now: datetime
) -> None:
    """Pack flashcards become review cards; user edits and FSRS state are preserved."""
    card = await db.scalar(
        select(ReviewCard).where(
            ReviewCard.source_kind == "flashcard", ReviewCard.source_item_id == item.id
        )
    )
    if card is None:
        config = await get_default_config(db)
        scheduler = build_scheduler(config)
        state = scheduler.new_card(now)
        db.add(
            ReviewCard(
                source_kind="flashcard",
                source_item_id=item.id,
                front_md=spec.front_md,
                back_md=spec.back_md,
                state=state.state,
                step=state.step,
                stability=state.stability,
                difficulty=state.difficulty,
                due=state.due,
                last_review=state.last_review,
                scheduler_config_id=config.id,
                scheduler_version=scheduler.version,
            )
        )
    elif not card.user_edited:
        card.front_md, card.back_md = spec.front_md, spec.back_md
    await db.flush()


async def _retire_missing(
    db: AsyncSession, pack: ContentPack, seen_keys: set[str], report: ImportReport
) -> None:
    rows = await db.scalars(
        select(ContentItem).where(
            ContentItem.pack_id == pack.id,
            ContentItem.status == "active",
            ContentItem.item_key.not_in(list(seen_keys) or ["-"]),
        )
    )
    for item in rows.all():
        item.status = "retired"
        report.retired.append(item.item_key)
