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
from collections.abc import Iterable, Mapping
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
) -> Query:
    """The objective's words, weighted by where they come from: the title counts most, the
    knowledge and skills statements and mapped lesson titles next, bodies and stems once."""
    weights: defaultdict[str, float] = defaultdict(float)
    for term in tokenize(title):
        weights[term] += 3.0
    for source, weight in ((statements, 2.0), (lesson_titles, 2.0), (question_stems, 1.0)):
        for text in source:
            for term in set(tokenize(text)):
                weights[term] += weight
    for text in lesson_bodies:
        for term in set(tokenize(text)[:LESSON_BODY_TOKENS]):
            weights[term] += 1.0
    return Query(code=code, domain_code=domain_code, weights=dict(weights))


def specificity(queries: Iterable[Query]) -> dict[str, float]:
    """How much a term tells objectives apart: a term in every objective's query says
    nothing (weight near 0); a term in one objective's query says a lot."""
    queries = list(queries)
    count: Counter[str] = Counter()
    for query in queries:
        count.update(set(query.weights))
    total = len(queries)
    return {term: math.log((total + 1) / (seen + 0.5)) for term, seen in count.items()}


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

    def score(
        self, doc: Document, query: Query, spec: Mapping[str, float]
    ) -> tuple[float, list[tuple[str, float]]]:
        """The BM25 score and each matched term's contribution, largest first."""
        if doc.length == 0 or self.avg_length == 0:
            return 0.0, []
        norm = K1 * (1 - B + B * doc.length / self.avg_length)
        contributions: list[tuple[str, float]] = []
        for term, weight in query.weights.items():
            tf = doc.terms.get(term, 0)
            if not tf:
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
) -> list[Scored]:
    """The objectives a lecture is about: the few that score close to its best match and
    share enough terms to show why. A title hint for a domain lifts its objectives."""
    hints = set(hinted_domains)
    scored: list[tuple[str, float, tuple[str, ...]]] = []
    for query in queries:
        score, contributions = index.score(doc, query, spec)
        if query.domain_code in hints:
            score *= DOMAIN_HINT_BOOST
        matched = tuple(term for term, _ in contributions[:MATCHED_TERMS_SHOWN])
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
