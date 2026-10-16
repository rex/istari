"""Lectures ranked against objectives: a weighted query per objective, BM25 over the
candidate lectures, and the cut that keeps a lecture's few best objectives. Pure.

A lecture is a bag of transcript terms (`lecture_text`). An objective is a weighted query
built from its title, knowledge and skills statements and the lessons and questions already
mapped to it. BM25 scores every lecture against every objective; a lecture keeps the
objectives that stand clearly above the rest and share enough terms to be explainable.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from collections.abc import Collection, Iterable, Mapping
from dataclasses import dataclass

from app.domain.lecture_text import Document, tokenize

K1 = 1.5
B = 0.75
MAX_OBJECTIVES_PER_LECTURE = 3
MIN_NORMALIZED = 0.5
MIN_MATCHED_TERMS = 3
MATCHED_TERMS_SHOWN = 8
DOMAIN_HINT_BOOST = 1.5
LESSON_BODY_TOKENS = 400
# Measured on a hand-labelled SAA-C03 sample (2026-10-16, rex/istari#67): a term in more
# than 40% of the lectures says nothing about one of them, and dividing by the query's mass
# stops the objectives with the most lessons and questions from winning on count alone.
GENERIC_SHARE = 0.4
MASS_POWER = 1.0
# A corpus this small makes every term generic; the share rule needs more lectures than this.
MIN_DOCS_FOR_GENERIC = 20


@dataclass(frozen=True, slots=True)
class Query:
    code: str
    domain_code: str
    weights: Mapping[str, float]


def objective_query(
    code: str,
    domain_code: str,
    title: str,
    statements: Iterable[str],
    lesson_titles: Iterable[str],
    lesson_bodies: Iterable[str],
    question_stems: Iterable[str],
    *,
    body_weight: float = 1.0,
    stem_weight: float = 1.0,
) -> Query:
    """The objective's words, weighted by where they come from: the title counts most, the
    knowledge and skills statements and mapped lesson titles next, bodies and stems once."""
    weights: defaultdict[str, float] = defaultdict(float)
    for term in tokenize(title):
        weights[term] += 3.0
    for source, weight in ((statements, 2.0), (lesson_titles, 2.0), (question_stems, stem_weight)):
        for text in source:
            for term in set(tokenize(text)):
                weights[term] += weight
    for text in lesson_bodies:
        for term in set(tokenize(text)[:LESSON_BODY_TOKENS]):
            weights[term] += body_weight
    return Query(
        code=code, domain_code=domain_code, weights={t: w for t, w in weights.items() if w > 0}
    )


def specificity(queries: Iterable[Query]) -> dict[str, float]:
    """How much a term tells objectives apart: a term in every objective's query says
    nothing (weight near 0); a term in one objective's query says a lot."""
    queries = list(queries)
    count: Counter[str] = Counter()
    for query in queries:
        count.update(set(query.weights))
    total = len(queries)
    return {term: math.log((total + 1) / (seen + 0.5)) for term, seen in count.items()}


def query_mass(query: Query, spec: Mapping[str, float]) -> float:
    """How much a query can score at most: the sum of its weighted, specific terms. A big
    query (many lessons and questions mapped) wins on count alone unless divided by it."""
    return sum(weight * spec.get(term, 1.0) for term, weight in query.weights.items())


@dataclass(frozen=True, slots=True)
class Scored:
    key: str
    code: str
    score: float
    normalized: float
    matched: tuple[str, ...]


class Index:
    """BM25 over a set of documents (the candidate lectures of one track)."""

    def __init__(self, docs: Iterable[Document]) -> None:
        self.docs = list(docs)
        self.size = len(self.docs)
        self.avg_length = sum(doc.length for doc in self.docs) / self.size if self.size else 0.0
        self.df: Counter[str] = Counter()
        for doc in self.docs:
            self.df.update(set(doc.terms))

    def idf(self, term: str) -> float:
        seen = self.df.get(term, 0)
        return math.log(1 + (self.size - seen + 0.5) / (seen + 0.5))

    def generic(self, share: float) -> set[str]:
        """Terms in more than `share` of the lectures: they say what the corpus is about,
        not what one lecture is about."""
        if self.size < MIN_DOCS_FOR_GENERIC or share >= 1:
            return set()
        return {term for term, seen in self.df.items() if seen / self.size > share}

    def score(
        self,
        doc: Document,
        query: Query,
        spec: Mapping[str, float],
        skip: Collection[str] = (),
    ) -> tuple[float, list[tuple[str, float]]]:
        """The BM25 score and each matched term's contribution, largest first."""
        if doc.length == 0 or self.avg_length == 0:
            return 0.0, []
        norm = K1 * (1 - B + B * doc.length / self.avg_length)
        contributions: list[tuple[str, float]] = []
        for term, weight in query.weights.items():
            tf = doc.terms.get(term, 0)
            if not tf or term in skip:
                continue
            part = weight * spec.get(term, 1.0) * self.idf(term) * (tf * (K1 + 1)) / (tf + norm)
            if part > 0:
                contributions.append((term, part))
        contributions.sort(key=lambda item: (-item[1], item[0]))
        return sum(part for _, part in contributions), contributions


def rank_lecture(
    index: Index,
    doc: Document,
    queries: Iterable[Query],
    spec: Mapping[str, float],
    hinted_domains: Iterable[str] = (),
    *,
    ceilings: Mapping[str, float] | None = None,
    floor: float = 0.0,
    generic: Collection[str] = (),
    mass: Mapping[str, float] | None = None,
    mass_power: float = 0.0,
    boosts: Mapping[str, float] | None = None,
) -> list[Scored]:
    """The objectives a lecture is about: the few that score close to its best match and
    share enough terms to show why. A title hint for a domain lifts its objectives. With
    `ceilings` (each objective's best score over the corpus) a match below `floor` of its
    objective's ceiling is dropped, so a lecture about nothing in particular maps to
    nothing; `generic` terms are left out of the scoring."""
    hints = set(hinted_domains)
    scored: list[tuple[str, float, tuple[str, ...]]] = []
    for query in queries:
        score, contributions = index.score(doc, query, spec, generic)
        if mass is not None and mass_power > 0 and mass.get(query.code, 0.0) > 0:
            score /= mass[query.code] ** mass_power
        if query.domain_code in hints:
            score *= DOMAIN_HINT_BOOST
        if boosts:
            score *= boosts.get(query.code, 1.0)
        matched = tuple(term for term, _ in contributions[:MATCHED_TERMS_SHOWN])
        if ceilings is not None and score < floor * ceilings.get(query.code, 0.0):
            continue
        if score > 0 and len(contributions) >= MIN_MATCHED_TERMS:
            scored.append((query.code, score, matched))
    if not scored:
        return []
    best = max(score for _, score, _ in scored)
    scored.sort(key=lambda item: (-item[1], item[0]))
    return [
        Scored(key=doc.key, code=code, score=score, normalized=score / best, matched=matched)
        for code, score, matched in scored[:MAX_OBJECTIVES_PER_LECTURE]
        if score / best >= MIN_NORMALIZED
    ]
