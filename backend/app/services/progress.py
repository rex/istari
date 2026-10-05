"""The Progress view. Evidence is labelled; nothing is turned into a readiness score."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import ExamVersion, UserSettings
from app.contracts.common import ObjectiveRef
from app.contracts.progress import (
    ActivityDay,
    ConfidentMistakeView,
    DomainProgress,
    EvidenceLevel,
    ObjectiveProgress,
    ProgressFlags,
    ProgressTotals,
    ProgressView,
)
from app.domain.recommendation import MIN_EVIDENCE, WEAK_THRESHOLD
from app.domain.timeframes import local_date
from app.services.content_query import content_str, objective_refs
from app.services.progress_activity import (
    activity_by_day,
    assessment_session_count,
    card_counts,
    confident_mistakes,
    lesson_counts,
)
from app.services.progress_queries import (
    ObjectiveCounts,
    answer_facts,
    invalidation_flags,
    item_counts_by_objective,
)
from app.services.today import block_view, build_plan
from app.services.track import track_view

EVIDENCE_NOTE = (
    "First-attempt accuracy counts the first time you answered each question family. "
    "Repeated practice is shown separately and is not evidence of exam readiness. "
    f"An objective needs at least {MIN_EVIDENCE} first attempts before it is rated."
)


def _ratio(correct: int, total: int) -> float | None:
    return (correct / total) if total else None


def evidence_level(first_attempts: int, first_correct: int) -> EvidenceLevel:
    if first_attempts < MIN_EVIDENCE:
        return "insufficient"
    accuracy = first_correct / first_attempts
    if accuracy < WEAK_THRESHOLD:
        return "weak"
    if accuracy < 0.85:
        return "developing"
    return "solid"


def _objective_progress(
    ref: ObjectiveRef, counts: ObjectiveCounts, familiar: set[str]
) -> ObjectiveProgress:
    return ObjectiveProgress(
        code=ref.code,
        title=ref.title,
        domain_code=ref.domain_code,
        lessons_total=counts.lessons_total,
        lessons_completed=counts.lessons_completed,
        questions_total=counts.questions_total,
        families_seen=counts.families_seen,
        first_attempts=counts.first_attempts,
        first_correct=counts.first_correct,
        first_accuracy=_ratio(counts.first_correct, counts.first_attempts),
        repeat_attempts=counts.repeat_attempts,
        repeat_correct=counts.repeat_correct,
        repeat_accuracy=_ratio(counts.repeat_correct, counts.repeat_attempts),
        assessment_attempts=counts.assessment_attempts,
        assessment_correct=counts.assessment_correct,
        evidence=evidence_level(counts.first_attempts, counts.first_correct),
        self_declared_familiar=ref.code in familiar,
    )


async def build_progress(
    db: AsyncSession,
    *,
    settings: UserSettings,
    exam: ExamVersion,
    now: datetime,
    objective_map: dict[str, ObjectiveRef],
) -> ProgressView:
    track = await track_view(db, exam.id)
    counts = await item_counts_by_objective(db, exam_version_id=exam.id)
    facts = await answer_facts(db, exam_version_id=exam.id)
    families_by_objective: dict[str, set[str]] = {}
    totals = ObjectiveCounts()
    families_total: set[str] = set()
    for fact in facts:
        families_total.add(fact.family_key)
        _tally(totals, fact)
        for code in fact.objectives:
            bucket = counts.setdefault(code, ObjectiveCounts())
            _tally(bucket, fact)
            families_by_objective.setdefault(code, set()).add(fact.family_key)
    for code, families in families_by_objective.items():
        counts[code].families_seen = len(families)
    totals.families_seen = len(families_total)
    totals.questions_total = sum(c.questions_total for c in counts.values())
    # A lesson teaching several objectives is counted once here, not once per objective.
    lesson_totals, lessons_by_domain = await lesson_counts(db, exam_version_id=exam.id)
    totals.lessons_total, totals.lessons_completed = lesson_totals

    familiar = set(settings.familiar_objective_codes)
    domains: list[DomainProgress] = []
    all_objectives: list[ObjectiveProgress] = []
    for domain in track.domains:
        objectives = [
            _objective_progress(
                objective_map[o.code], counts.get(o.code, ObjectiveCounts()), familiar
            )
            for o in domain.objectives
            if o.code in objective_map
        ]
        all_objectives.extend(objectives)
        first_attempts = sum(o.first_attempts for o in objectives)
        first_correct = sum(o.first_correct for o in objectives)
        domains.append(
            DomainProgress(
                code=domain.code,
                name=domain.name,
                weight_percent=domain.weight_percent,
                objectives=objectives,
                first_attempts=first_attempts,
                first_correct=first_correct,
                first_accuracy=_ratio(first_correct, first_attempts),
                lessons_total=lessons_by_domain.get(domain.code, (0, 0))[0],
                lessons_completed=lessons_by_domain.get(domain.code, (0, 0))[1],
            )
        )
    weak = sorted(
        (o for o in all_objectives if o.evidence == "weak"),
        key=lambda o: (o.first_accuracy or 0.0, -o.first_attempts, o.code),
    )

    invalidated_items, excluded_answers = await invalidation_flags(db, exam_version_id=exam.id)
    cards_total, cards_due = await card_counts(db, now=now)
    plan, _active = await build_plan(
        db,
        settings=settings,
        exam=exam,
        now=now,
        minutes=settings.preferred_session_minutes,
        objective_map=objective_map,
    )
    mistakes = [
        ConfidentMistakeView(
            item_key=item.item_key,
            stem_md=content_str(rev, "stem_md"),
            objectives=objective_refs(rev.objective_codes, objective_map),
            answered_at=answer.answered_at,
            session_id=answer.session_id,
            has_card=has_card,
        )
        for answer, item, rev, has_card in await confident_mistakes(db, exam_version_id=exam.id)
    ]
    return ProgressView(
        totals=ProgressTotals(
            first_attempts=totals.first_attempts,
            first_correct=totals.first_correct,
            first_accuracy=_ratio(totals.first_correct, totals.first_attempts),
            repeat_attempts=totals.repeat_attempts,
            repeat_correct=totals.repeat_correct,
            repeat_accuracy=_ratio(totals.repeat_correct, totals.repeat_attempts),
            assessment_attempts=totals.assessment_attempts,
            assessment_correct=totals.assessment_correct,
            assessment_sessions=await assessment_session_count(db),
            lessons_total=totals.lessons_total,
            lessons_completed=totals.lessons_completed,
            cards_total=cards_total,
            cards_due=cards_due,
            questions_total=totals.questions_total,
            families_seen=totals.families_seen,
        ),
        domains=domains,
        weak_areas=weak,
        confident_mistakes=mistakes,
        recent_activity=await _activity(db, now=now, tz=settings.timezone),
        flags=ProgressFlags(
            invalidated_items=invalidated_items,
            excluded_answers=excluded_answers,
            note="Answers on invalidated questions are excluded from every figure above."
            if invalidated_items
            else "No invalidated questions.",
        ),
        next_action=block_view(plan.blocks[0]) if plan.blocks else None,
        evidence_note=EVIDENCE_NOTE,
    )


def _tally(bucket: ObjectiveCounts, fact: object) -> None:
    from app.services.progress_queries import (
        AnswerFacts,
    )

    assert isinstance(fact, AnswerFacts)
    if fact.first_attempt:
        bucket.first_attempts += 1
        bucket.first_correct += int(fact.is_correct)
    else:
        bucket.repeat_attempts += 1
        bucket.repeat_correct += int(fact.is_correct)
    if fact.session_kind == "assessment":
        bucket.assessment_attempts += 1
        bucket.assessment_correct += int(fact.is_correct)


async def _activity(db: AsyncSession, *, now: datetime, tz: str) -> list[ActivityDay]:
    by_day = await activity_by_day(db, now=now, tz=tz)
    today: date = local_date(now, tz)
    days: list[ActivityDay] = []
    for offset in range(13, -1, -1):
        day = today - timedelta(days=offset)
        counts = by_day.get(day.isoformat(), {"answers": 0, "reviews": 0, "lessons": 0})
        days.append(
            ActivityDay(
                date=day,
                answers=counts["answers"],
                reviews=counts["reviews"],
                lessons=counts["lessons"],
            )
        )
    return days
