"""Turn parsed third-party questions into a private pack in Istari's schema.

The pack is honest about what it is: every item is `draft`, authored by the vendor,
not source-checked, with the exam version suffixed `-DRILL` so the drill track never
mixes its domains into a verified public pack. Groups (a quiz name, a practice test
number) become domains, so Progress can still say which topic is weak.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date

MIN_DISTRACTORS = 2
MAX_OPTIONS = 6
GENERIC_RATIONALE = "Not the best fit for this scenario; the explanation says why."
IMPORT_NOTE = (
    "Imported from purchased course material for personal study. Not reviewed, not "
    "source-checked, not for redistribution."
)


@dataclass(slots=True)
class ParsedQuestion:
    stem: str
    options: list[str]
    correct: list[int]
    explanation: str = ""
    rationales: dict[int, str] = field(default_factory=dict)
    references: list[str] = field(default_factory=list)
    group: str = ""


@dataclass(frozen=True, slots=True)
class PrivatePackMeta:
    slug: str
    name: str
    vendor: str
    exam_code: str
    exam_name: str
    certification_slug: str
    certification_name: str
    authored_on: date
    source_title: str
    source_url: str = "https://www.udemy.com/"
    subject_slug: str = "aws"
    subject_name: str = "Amazon Web Services"


def question_slug(stem: str) -> str:
    """Stable across re-runs: the same stem always maps to the same item."""
    digest = hashlib.sha1(stem.strip().casefold().encode("utf-8")).hexdigest()  # noqa: S324 - not security
    return f"q-{digest[:12]}"


def _item(q: ParsedQuestion, meta: PrivatePackMeta, objective: str) -> dict[str, object]:
    ids = [f"o{i + 1}" for i in range(len(q.options))]
    correct_ids = [ids[i] for i in q.correct]
    rationales = {
        ids[i]: (q.rationales.get(i) or GENERIC_RATIONALE)
        for i in range(len(q.options))
        if i not in q.correct
    }
    checked = meta.authored_on.isoformat()
    sources: list[dict[str, str]] = [
        {"title": url, "url": url, "checked_on": checked} for url in q.references
    ] or [{"title": meta.source_title, "url": meta.source_url, "checked_on": checked}]
    return {
        "slug": question_slug(q.stem),
        "objectives": [objective],
        "sources": sources,
        "provenance": {
            "authored_by": "human",
            "author": meta.vendor,
            "authored_on": checked,
            "source_checked": False,
            "notes": IMPORT_NOTE,
        },
        "review_status": "draft",
        "tags": ["imported", meta.slug],
        "difficulty": "medium",
        "stem_md": q.stem,
        "select_count": len(correct_ids),
        "options": [{"id": oid, "text_md": text} for oid, text in zip(ids, q.options, strict=True)],
        "correct_option_ids": correct_ids,
        "explanation_md": q.explanation or "No explanation was provided in the source.",
        "distractor_rationales": rationales,
        "decisive_constraint": "Not analysed; imported question.",
    }


def reject_reason(q: ParsedQuestion) -> str | None:
    """Why a parsed question cannot become a valid item, or None when it can."""
    if not q.stem.strip():
        return "empty stem"
    if not q.correct or any(i >= len(q.options) for i in q.correct):
        return "no usable correct answer"
    if len(q.options) > MAX_OPTIONS:
        return f"more than {MAX_OPTIONS} options"
    if len(q.options) - len(set(q.correct)) < MIN_DISTRACTORS:
        return "fewer than two distractors"
    if len({o.strip().casefold() for o in q.options}) != len(q.options):
        return "duplicate option texts"
    return None


def build_private_pack(
    questions: list[ParsedQuestion], meta: PrivatePackMeta
) -> tuple[dict[str, object], list[tuple[ParsedQuestion, str]]]:
    """The pack document plus the questions that were rejected and why."""
    kept: list[ParsedQuestion] = []
    rejected: list[tuple[ParsedQuestion, str]] = []
    seen: set[str] = set()
    for q in questions:
        reason = reject_reason(q)
        if reason is None and question_slug(q.stem) in seen:
            reason = "duplicate stem"
        if reason is not None:
            rejected.append((q, reason))
            continue
        seen.add(question_slug(q.stem))
        kept.append(q)
    groups: list[str] = []
    for q in kept:
        label = q.group.strip() or "Imported"
        if label not in groups:
            groups.append(label)
    # Weights must sum to exactly 100: an even split, the remainder on the first groups.
    base, extra = divmod(100, max(1, len(groups)))
    domains = [
        {
            "code": str(i),
            "name": label,
            "weight_percent": base + (1 if i <= extra else 0),
            "objectives": [{"code": f"{i}.1", "title": label, "knowledge": [], "skills": []}],
        }
        for i, label in enumerate(groups, start=1)
    ]
    items = [_item(q, meta, f"{groups.index(q.group.strip() or 'Imported') + 1}.1") for q in kept]
    pack = {
        "schema_version": 1,
        "pack": {
            "slug": meta.slug,
            "name": meta.name,
            "version": "1.0.0",
            "description": f"Private drill pack imported from {meta.vendor}. {IMPORT_NOTE}",
            "authored_by": "human",
            "coverage_notes_md": (
                f"Drill material for {meta.exam_code}: {len(items)} imported questions in "
                f"{len(groups)} groups. Facts may be out of date; nothing here is verified."
            ),
        },
        "subject": {"slug": meta.subject_slug, "name": meta.subject_name},
        "certification": {
            "slug": meta.certification_slug,
            "name": meta.certification_name,
            "provider": "Amazon Web Services",
        },
        "exam_version": {
            "code": f"{meta.exam_code}-DRILL",
            "name": f"{meta.exam_name} (drill, imported)",
            "guide_revision": None,
            "duration_minutes": 130,
            "scored_questions": 65,
            "unscored_questions": 0,
            "passing_scaled_score": 720,
            "score_scale": [100, 1000],
            "format_notes": (
                "Drill track built from imported material; exam facts are placeholders."
            ),
            "verification": {"status": "unverified", "checked_on": None, "sources": []},
        },
        "domains": domains,
        "lessons": [],
        "questions": items,
        "flashcards": [],
        "labs": [],
    }
    return pack, rejected
