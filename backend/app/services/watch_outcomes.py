"""What watching did. Per objective: the mapped lectures the owner has watched to the end,
and the first-attempt answers on that objective split at the first of those watches. Per
course: the first attempts on an objective after a lecture of that course mapped to it was
watched. Small samples, shown next to the evidence as coverage and correlation, never as
mastery."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import (
    CourseProgress,
    Domain,
    ExamVersion,
    LectureObjective,
    Objective,
)
from app.contracts.watch_outcomes import WatchOutcome
from app.services.progress_queries import AnswerFacts


@dataclass(slots=True)
class Watched:
    """The mapped lectures watched under one key (an objective, or a course and objective)."""

    lectures: set[tuple[str, str]] = field(default_factory=set)
    first_at: datetime | None = None

    def add(self, key: tuple[str, str], at: datetime) -> None:
        self.lectures.add(key)
        self.first_at = at if self.first_at is None or at < self.first_at else self.first_at


def bucket_answers(watched: Watched, answers: Iterable[tuple[datetime, bool]]) -> WatchOutcome:
    """First attempts before and after the first watch; all "before" when nothing is watched."""
    before = [
        correct for at, correct in answers if watched.first_at is None or at < watched.first_at
    ]
    after = [
        correct
        for at, correct in answers
        if watched.first_at is not None and at >= watched.first_at
    ]
    return WatchOutcome(
        lectures_watched=len(watched.lectures),
        first_watched_at=watched.first_at,
        before_attempts=len(before),
        before_correct=sum(1 for correct in before if correct),
        after_attempts=len(after),
        after_correct=sum(1 for correct in after if correct),
    )


async def _watched_rows(
    db: AsyncSession, exam: ExamVersion
) -> list[tuple[str, str, str, datetime]]:
    """(course_slug, lecture_path, objective code, completed_at) for every watched mapping."""
    rows = await db.execute(
        select(
            LectureObjective.course_slug,
            LectureObjective.lecture_path,
            Objective.code,
            CourseProgress.completed_at,
        )
        .join(Objective, Objective.id == LectureObjective.objective_id)
        .join(Domain, Domain.id == Objective.domain_id)
        .join(
            CourseProgress,
            (CourseProgress.course_slug == LectureObjective.course_slug)
            & (CourseProgress.lecture_path == LectureObjective.lecture_path),
        )
        .where(
            LectureObjective.exam_version_id == exam.id,
            LectureObjective.source != "excluded",
            CourseProgress.completed_at.is_not(None),
        )
    )
    return [(str(s), str(p), str(c), at) for s, p, c, at in rows.all() if at is not None]


def _answers_by_objective(facts: Iterable[AnswerFacts]) -> dict[str, list[tuple[datetime, bool]]]:
    out: dict[str, list[tuple[datetime, bool]]] = defaultdict(list)
    for fact in facts:
        if not fact.first_attempt:
            continue
        for code in fact.objectives:
            out[code].append((fact.answered_at, fact.is_correct))
    return out


async def objective_outcomes(
    db: AsyncSession, exam: ExamVersion, facts: Iterable[AnswerFacts]
) -> dict[str, WatchOutcome]:
    """Per objective code, for the objectives with at least one watched lecture."""
    watched: dict[str, Watched] = defaultdict(Watched)
    for slug, path, code, at in await _watched_rows(db, exam):
        watched[code].add((slug, path), at)
    answers = _answers_by_objective(facts)
    return {code: bucket_answers(w, answers.get(code, [])) for code, w in watched.items()}


async def course_outcomes(
    db: AsyncSession, exam: ExamVersion, facts: Iterable[AnswerFacts]
) -> dict[str, tuple[int, int]]:
    """Per course slug: first attempts (count, correct) on an objective after a lecture of
    that course mapped to it was watched."""
    watched: dict[tuple[str, str], Watched] = defaultdict(Watched)
    for slug, path, code, at in await _watched_rows(db, exam):
        watched[(slug, code)].add((slug, path), at)
    answers = _answers_by_objective(facts)
    out: dict[str, tuple[int, int]] = defaultdict(lambda: (0, 0))
    for (slug, code), w in watched.items():
        outcome = bucket_answers(w, answers.get(code, []))
        attempts, correct = out[slug]
        out[slug] = (attempts + outcome.after_attempts, correct + outcome.after_correct)
    return dict(out)
