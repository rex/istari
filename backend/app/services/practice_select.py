"""Choose the questions for a session. Deterministic given a seed; documented order.

Priority groups (within a focus):
  1. `unseen`  — question families never answered.
  2. `retry`   — families whose latest answer was wrong; confident mistakes first,
                 then oldest answer first.
  3. `repeat`  — families answered correctly, least recently answered first.
For `mixed` focus the unseen group is drawn in weighted round-robin across
domains (heaviest domain first) so a short session still spans the exam.
A family never appears twice in one session.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import Answer, ContentItem, ContentRevision, Domain
from app.contracts.common import ObjectiveRef
from app.services.content_query import list_items, objective_codes_for_items


@dataclass(slots=True)
class Candidate:
    item: ContentItem
    revision: ContentRevision
    objectives: list[str]
    domain_code: str
    group: str


@dataclass(frozen=True, slots=True)
class _History:
    last_at: datetime
    last_correct: bool
    confident_wrong: bool


async def _family_history(db: AsyncSession) -> dict[str, _History]:
    latest = (
        select(Answer.family_key, func.max(Answer.answered_at).label("last_at"))
        .group_by(Answer.family_key)
        .subquery()
    )
    rows = await db.execute(
        select(Answer.family_key, Answer.answered_at, Answer.is_correct, Answer.confidence).join(
            latest,
            (latest.c.family_key == Answer.family_key) & (latest.c.last_at == Answer.answered_at),
        )
    )
    out: dict[str, _History] = {}
    for family, at, correct, confidence in rows.all():
        out[family] = _History(
            last_at=at,
            last_correct=bool(correct),
            confident_wrong=(not correct and confidence == "confident"),
        )
    return out


async def _domain_weights(db: AsyncSession, exam_version_id: int) -> dict[str, int]:
    rows = await db.execute(
        select(Domain.code, Domain.weight_percent).where(Domain.exam_version_id == exam_version_id)
    )
    return dict(rows.all())


def _round_robin(groups: dict[str, list[Candidate]], order: list[str]) -> list[Candidate]:
    out: list[Candidate] = []
    queues = {code: list(items) for code, items in groups.items()}
    while any(queues.values()):
        for code in order:
            queue = queues.get(code)
            if queue:
                out.append(queue.pop(0))
    return out


async def select_questions(
    db: AsyncSession,
    *,
    exam_version_id: int,
    focus: str,
    count: int,
    seed: int,
    objective_map: dict[str, ObjectiveRef],
) -> tuple[list[Candidate], dict[str, object]]:
    rows = await list_items(db, exam_version_id=exam_version_id, kind="question", usable_only=True)
    codes = await objective_codes_for_items(db, (item.id for item, _ in rows))
    history = await _family_history(db)
    weights = await _domain_weights(db, exam_version_id)
    rng = random.Random(seed)  # noqa: S311 - ordering only

    candidates: list[Candidate] = []
    for item, revision in rows:
        objectives = codes.get(item.id, [])
        domain_code = objective_map[objectives[0]].domain_code if objectives else "?"
        hist = history.get(item.family_key)
        group = "unseen" if hist is None else ("retry" if not hist.last_correct else "repeat")
        candidates.append(Candidate(item, revision, objectives, domain_code, group))
    rng.shuffle(candidates)

    target_code = focus.removeprefix("objective:") if focus.startswith("objective:") else None
    in_focus = [c for c in candidates if target_code is None or target_code in c.objectives]
    out_of_focus = [
        c for c in candidates if target_code is not None and target_code not in c.objectives
    ]

    ordered: list[Candidate] = []
    for pool in (in_focus, out_of_focus):
        unseen = [c for c in pool if c.group == "unseen"]
        if target_code is None:
            by_domain: dict[str, list[Candidate]] = {}
            for c in unseen:
                by_domain.setdefault(c.domain_code, []).append(c)
            domain_order = sorted(by_domain, key=lambda d: (-weights.get(d, 0), d))
            unseen = _round_robin(by_domain, domain_order)
        retry = sorted(
            (c for c in pool if c.group == "retry"),
            key=lambda c: (
                not history[c.item.family_key].confident_wrong,
                history[c.item.family_key].last_at,
            ),
        )
        repeat = sorted(
            (c for c in pool if c.group == "repeat"),
            key=lambda c: history[c.item.family_key].last_at,
        )
        ordered.extend([*unseen, *retry, *repeat])

    chosen: list[Candidate] = []
    families: set[str] = set()
    for c in ordered:
        if c.item.family_key in families:
            continue
        families.add(c.item.family_key)
        chosen.append(c)
        if len(chosen) >= count:
            break

    explanation: dict[str, object] = {
        "focus": focus,
        "requested": count,
        "pool_size": len(candidates),
        "groups": {
            g: sum(1 for c in chosen if c.group == g) for g in ("unseen", "retry", "repeat")
        },
        "out_of_focus_fill": sum(
            1 for c in chosen if target_code and target_code not in c.objectives
        ),
        "order_policy": (
            "unseen (domain round-robin for mixed) > retry (confident mistakes first) > repeat"
        ),
    }
    return chosen, explanation
