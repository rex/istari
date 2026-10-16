"""Measure the lecture ranking against a hand-labelled sample under a parameter set, without
touching the share: the index's stored term counts are re-ranked in process. The sample
names lectures by course slug and path with the objectives they teach (none for a course
introduction); it lives outside the repository, with the corpus."""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import ExamVersion, IndexedLecture
from app.domain.lecture_index import (
    GENERIC_SHARE,
    MASS_POWER,
    Index,
    Query,
    query_mass,
    rank_lecture,
    specificity,
)
from app.domain.lecture_rules import (
    distinctive_domain_terms,
    domain_hints,
    is_housekeeping,
    rule_codes,
)
from app.domain.lecture_text import Document
from app.domain.naming import natural_key
from app.services.lecture_index import objective_queries


@dataclass(frozen=True, slots=True)
class Params:
    """The levers: a floor against each objective's best score over the corpus, the share of
    lectures past which a term is generic, and the weight of lesson bodies and stems."""

    floor: float = 0.0
    generic_share: float = GENERIC_SHARE
    body_weight: float = 1.0
    stem_weight: float = 1.0
    # Which point of an objective's score distribution over the corpus is its ceiling: 1.0
    # is the single best lecture, which one outlier can set; 0.9 is the 90th percentile.
    ceiling_quantile: float = 1.0
    # Divide a score by the query's mass to this power: 0 leaves big queries their edge,
    # 0.5 halves it, 1 removes it.
    mass_power: float = MASS_POWER
    # Multiply a lecture's score for the objectives its whole section ranks highest: the
    # section a lecture sits in says what it is about. 1 is off (measured: no gain).
    section_boost: float = 1.0
    # Leave a welcome, a course tour or a support lecture unmapped, as the build does.
    skip_housekeeping: bool = True


@dataclass(frozen=True, slots=True)
class Labelled:
    course_slug: str
    lecture_path: str
    title: str
    objectives: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Verdict:
    title: str
    labels: tuple[str, ...]
    predicted: tuple[str, ...]

    @property
    def top1(self) -> bool:
        return bool(self.predicted) and self.predicted[0] in self.labels

    @property
    def hit3(self) -> bool:
        return any(code in self.labels for code in self.predicted)


@dataclass(slots=True)
class EvalReport:
    params: Params
    verdicts: list[Verdict] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)

    @property
    def labelled(self) -> list[Verdict]:
        return [v for v in self.verdicts if v.labels]

    @property
    def unlabelled(self) -> list[Verdict]:
        return [v for v in self.verdicts if not v.labels]

    def lines(self) -> list[str]:
        """The summary a tuning run prints: rates, then every miss with what was predicted."""
        labelled, unlabelled = self.labelled, self.unlabelled
        top1 = sum(1 for v in labelled if v.top1)
        hit3 = sum(1 for v in labelled if v.hit3)
        clean = sum(1 for v in unlabelled if not v.predicted)
        candidates = sum(len(v.predicted) for v in self.verdicts)

        def pct(part: int, whole: int) -> str:
            return f"{100 * part / whole:.0f}%" if whole else "n/a"

        out = [
            f"params: {self.params}",
            f"labelled {len(labelled)}: top-1 {pct(top1, len(labelled))} ({top1}), "
            f"any of top-3 {pct(hit3, len(labelled))} ({hit3})",
            f"no objective {len(unlabelled)}: left unmapped "
            f"{pct(clean, len(unlabelled))} ({clean})",
            f"candidates per lecture {candidates / len(self.verdicts):.2f}"
            if self.verdicts
            else "no lectures",
        ]
        if self.missing:
            out.append(f"not in the index: {len(self.missing)}")
        for verdict in self.verdicts:
            if verdict.labels and not verdict.top1:
                out.append(
                    f"  miss  {verdict.title[:60]:60} want {', '.join(verdict.labels):10} "
                    f"got {', '.join(verdict.predicted) or '-'}"
                )
            elif not verdict.labels and verdict.predicted:
                out.append(f"  noise {verdict.title[:60]:60} got {', '.join(verdict.predicted)}")
        return out


def load_sample(path: Path) -> list[Labelled]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [
        Labelled(
            course_slug=str(item["course_slug"]),
            lecture_path=str(item["lecture_path"]),
            title=str(item.get("title", item["lecture_path"])),
            objectives=tuple(str(code) for code in item.get("objectives", [])),
        )
        for item in data["lectures"]
    ]


def _quantile(scores: list[float], quantile: float) -> float:
    """The score at `quantile` of the positive scores, 0 when there are none."""
    positive = sorted(score for score in scores if score > 0)
    if not positive:
        return 0.0
    position = min(len(positive) - 1, max(0, round(quantile * (len(positive) - 1))))
    return positive[position]


def _document(row: IndexedLecture) -> Document:
    terms = {
        str(term): int(count)
        for term, count in row.terms.items()
        if isinstance(count, int | float) and count > 0
    }
    return Document(
        key=f"{row.course_slug}/{row.lecture_path}", terms=terms, length=sum(terms.values())
    )


async def evaluate(
    db: AsyncSession, exam: ExamVersion, sample: list[Labelled], params: Params
) -> EvalReport:
    """Rank every lecture in the sample the way a build would, under `params`."""
    rows = (await db.scalars(select(IndexedLecture))).all()
    docs = {(r.course_slug, r.lecture_path): _document(r) for r in rows if r.terms}
    titles = {
        (r.course_slug, r.lecture_path): [r.lecture_title, r.lecture_path, r.section_title]
        for r in rows
    }
    sections = {(r.course_slug, r.lecture_path): r.section_title for r in rows}
    first_sections: dict[str, str] = {}
    for r in sorted(rows, key=lambda r: (r.course_slug, natural_key(r.lecture_path))):
        first_sections.setdefault(r.course_slug, r.section_title)
    index = Index(docs.values())
    queries, objectives, domains = await objective_queries(
        db, exam.id, body_weight=params.body_weight, stem_weight=params.stem_weight
    )
    spec = specificity(queries)
    distinctive = distinctive_domain_terms(domains)
    generic = index.generic(params.generic_share)
    mass = {query.code: query_mass(query, spec) for query in queries}

    def scaled(doc: Document, query: Query) -> float:
        score = index.score(doc, query, spec, generic)[0]
        if params.mass_power > 0 and mass[query.code] > 0:
            score /= mass[query.code] ** params.mass_power
        return score

    ceilings = (
        {
            query.code: _quantile(
                [scaled(doc, query) for doc in docs.values()], params.ceiling_quantile
            )
            for query in queries
        }
        if params.floor > 0
        else None
    )
    section_top = _section_top(rows, queries, index, scaled) if params.section_boost != 1.0 else {}
    report = EvalReport(params=params)
    for item in sample:
        key = (item.course_slug, item.lecture_path)
        doc = docs.get(key)
        if doc is None:
            report.missing.append(item.title)
            continue
        section = sections.get(key, "")
        if params.skip_housekeeping and is_housekeeping(
            titles[key][0], first_section=section == first_sections.get(key[0])
        ):
            report.verdicts.append(Verdict(item.title, item.objectives, ()))
            continue
        predicted = list(rule_codes(titles[key], objectives))
        boosts = dict.fromkeys(section_top.get((key[0], section), ()), params.section_boost)
        hits = rank_lecture(
            index,
            doc,
            queries,
            spec,
            domain_hints(titles[key], distinctive),
            ceilings=ceilings,
            floor=params.floor,
            generic=generic,
            mass=mass,
            mass_power=params.mass_power,
            boosts=boosts,
        )
        predicted.extend(hit.code for hit in hits if hit.code not in predicted)
        report.verdicts.append(Verdict(item.title, item.objectives, tuple(predicted)))
    return report


def _section_top(
    rows: Sequence[IndexedLecture],
    queries: Sequence[Query],
    index: Index,
    scaled: Callable[[Document, Query], float],
    keep: int = 2,
) -> dict[tuple[str, str], tuple[str, ...]]:
    """Each section's best objectives, from all its lectures' terms put together."""
    merged: dict[tuple[str, str], dict[str, int]] = defaultdict(dict)
    for row in rows:
        bucket = merged[(row.course_slug, row.section_title)]
        for term, count in row.terms.items():
            if isinstance(count, int | float) and count > 0:
                bucket[str(term)] = bucket.get(str(term), 0) + int(count)
    top: dict[tuple[str, str], tuple[str, ...]] = {}
    for key, terms in merged.items():
        doc = Document(key=f"{key[0]}/{key[1]}", terms=terms, length=sum(terms.values()))
        ranked = sorted(queries, key=lambda query: -scaled(doc, query))
        top[key] = tuple(query.code for query in ranked[:keep])
    return top
