"""Verified labs as evidence: which labs exist per objective, which were passed first time.

The honesty rule from the task-type proposal: a passed check is evidence for the lab's
objectives, counted once per lab, and only the *first* graded attempt decides "first-time
pass". Later attempts are repeats: shown, never hidden, never a penalty.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import ContentItem, ContentRevision, LabAttempt
from app.domain.planning_types import LabCandidate, ObjectiveEvidence
from app.domain.recommendation import weakest_objectives
from app.services.content_query import content_str, list_items, objective_codes_for_items
from app.services.lab_verifier import verifier_spec


@dataclass(slots=True)
class LabFact:
    item_key: str
    title: str
    estimated_minutes: int
    objectives: list[str] = field(default_factory=list)
    graded_attempts: int = 0
    # The first graded attempt's verdict; None until one exists.
    first_passed: bool | None = None
    ever_passed: bool = False


async def lab_facts(db: AsyncSession, *, exam_version_id: int) -> list[LabFact]:
    """Every active verified lab of the track with its objectives and attempt record."""
    rows = [
        (item, rev)
        for item, rev in await list_items(db, exam_version_id=exam_version_id, kind="lab")
        if verifier_spec(rev) is not None
    ]
    if not rows:
        return []
    item_ids = [item.id for item, _ in rows]
    codes = await objective_codes_for_items(db, item_ids)
    graded = await db.execute(
        select(LabAttempt.item_id, LabAttempt.passed)
        .where(LabAttempt.item_id.in_(item_ids), LabAttempt.checked_at.is_not(None))
        .order_by(LabAttempt.checked_at, LabAttempt.id)
    )
    facts: dict[int, LabFact] = {}
    for item, rev in rows:
        minutes = rev.content.get("estimated_minutes", 30)
        facts[item.id] = LabFact(
            item_key=item.item_key,
            title=content_str(rev, "title"),
            estimated_minutes=int(minutes) if isinstance(minutes, int) else 30,
            objectives=codes.get(item.id, []),
        )
    for item_id, passed in graded.all():
        fact = facts[int(item_id)]
        fact.graded_attempts += 1
        if fact.first_passed is None:
            fact.first_passed = bool(passed)
        fact.ever_passed = fact.ever_passed or bool(passed)
    return list(facts.values())


def pick_lab_candidate(
    facts: list[LabFact], evidence: tuple[ObjectiveEvidence, ...]
) -> LabCandidate | None:
    """The next verified lab to schedule: not yet passed, serving the weakest objective first.

    Among the labs that have never passed, prefer one whose objectives include the weakest
    rated objective; otherwise the first by key, so the order is stable and explainable.
    """
    open_labs = sorted((f for f in facts if not f.ever_passed), key=lambda f: f.item_key)
    if not open_labs:
        return None
    titles = {o.code: o.title for o in evidence}
    for weak in weakest_objectives(evidence):
        for fact in open_labs:
            if weak.code in fact.objectives:
                return _candidate(fact, weak.code, titles)
    first = open_labs[0]
    code = first.objectives[0] if first.objectives else ""
    return _candidate(first, code, titles)


def _candidate(fact: LabFact, code: str, titles: dict[str, str]) -> LabCandidate:
    return LabCandidate(
        item_key=fact.item_key,
        title=fact.title,
        estimated_minutes=fact.estimated_minutes,
        objective_code=code,
        objective_title=titles.get(code, ""),
    )


def _unused_type_guard(_: ContentItem | ContentRevision) -> None:  # pragma: no cover
    """Keeps the model imports meaningful for type checkers; never called."""
