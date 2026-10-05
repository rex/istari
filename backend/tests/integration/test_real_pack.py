"""The shipped SAA-C03 starter pack must validate, cover every task statement, and import."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from httpx import AsyncClient
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import ContentItem
from app.contracts.auth import OnboardingRequest
from app.domain.content.schemas.pack import ContentPackSpec
from app.domain.content.validate import parse_pack, validate_pack
from app.services.content_import import import_pack
from app.services.settings import complete_onboarding

PACK_PATH = (
    Path(__file__).resolve().parents[3] / "content" / "packs" / "aws-saa-c03-starter" / "pack.json"
)
EXPECTED_COUNTS = {"lessons": 8, "questions": 40, "flashcards": 24, "labs": 2}
TOTAL_ITEMS = sum(EXPECTED_COUNTS.values())


def _load() -> ContentPackSpec:
    return parse_pack(json.loads(PACK_PATH.read_text(encoding="utf-8")))


def test_pack_validates_and_matches_the_brief() -> None:
    spec = _load()
    report = validate_pack(spec)
    assert report.ok, report.errors
    assert {
        "lessons": len(spec.lessons),
        "questions": len(spec.questions),
        "flashcards": len(spec.flashcards),
        "labs": len(spec.labs),
    } == EXPECTED_COUNTS
    assert sum(q.select_count > 1 for q in spec.questions) >= 2, "multi-answer items expected"

    objective_codes = {o.code for d in spec.domains for o in d.objectives}
    questioned = {code for q in spec.questions for code in q.objectives}
    taught = {code for lesson in spec.lessons for code in lesson.objectives}
    assert questioned == objective_codes, "every task statement needs at least one question"
    assert taught == objective_codes, "every task statement needs a lesson"

    assert sum(d.weight_percent for d in spec.domains) == 100
    assert spec.exam_version.verification.status == "verified"
    assert spec.exam_version.scored_questions + spec.exam_version.unscored_questions == 65

    for item in (*spec.lessons, *spec.questions, *spec.flashcards, *spec.labs):
        assert item.provenance.authored_by == "ai", item.slug
        assert item.provenance.source_checked, item.slug
        assert item.review_status == "source_checked", item.slug
        assert all(s.url.startswith("https://") for s in item.sources), item.slug


async def test_pack_imports_and_reimport_is_a_no_op(db: AsyncSession) -> None:
    spec = _load()
    now = datetime.now(UTC)
    async with db.begin():
        first = await import_pack(db, spec, dry_run=False, now=now)
    assert first.counts()["created"] == TOTAL_ITEMS, first.counts()
    assert not first.track_changes

    async with db.begin():
        second = await import_pack(db, spec, dry_run=False, now=now)
    assert second.counts() == {"created": 0, "updated": 0, "unchanged": TOTAL_ITEMS, "retired": 0}
    assert await db.scalar(select(func.count(ContentItem.id))) == TOTAL_ITEMS


async def test_progress_counts_each_lesson_once(auth_client: AsyncClient, db: AsyncSession) -> None:
    """Four lessons teach more than one objective; the summary must still say eight."""
    now = datetime.now(UTC)
    async with db.begin():
        await import_pack(db, _load(), dry_run=False, now=now)
        exam_id = (await db.execute(text("SELECT id FROM exam_versions LIMIT 1"))).scalar_one()
        await complete_onboarding(
            db, OnboardingRequest(exam_version_id=exam_id, preferred_session_minutes=5), now=now
        )

    response = await auth_client.get("/api/progress")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["totals"]["lessons_total"] == EXPECTED_COUNTS["lessons"]
    assert body["totals"]["lessons_completed"] == 0
    assert {d["code"]: d["lessons_total"] for d in body["domains"]} == {
        "1": 2,
        "2": 2,
        "3": 2,
        "4": 2,
    }
    # Per-objective rows still count every lesson that teaches the objective.
    assert sum(o["lessons_total"] for d in body["domains"] for o in d["objectives"]) == 14
