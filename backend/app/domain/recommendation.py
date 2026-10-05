"""Explainable next-session planner. Pure function; no LLM, no I/O.

Documented policy (also summarised in docs/architecture.md):

Budgets by session length (reviews ≈ 20 s each, questions ≈ 60 s each):

    minutes  reviews  questions  lessons
       5        6         5         0
      15       10         8         0
      30       15        12         1

Order of blocks: resume an unfinished session → due reviews (capped by the
daily limit, and by 10 in backlog-recovery mode) → practice → one lesson.

Practice focus: the weakest objective that has at least MIN_EVIDENCE
first-attempt answers and accuracy below WEAK_THRESHOLD; otherwise a mixed
set. Tie-break for "weakest": lower accuracy, then more evidence, then higher
domain weight, then objective code ascending. Nothing here punishes missed
days: overdue reviews are simply "due", never "overdue by N days".
"""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.planning_types import (
    ObjectiveEvidence,
    Plan,
    PlanBlock,
    PlannerInput,
)

MIN_EVIDENCE = 3
WEAK_THRESHOLD = 0.7
RECOVERY_REVIEW_CAP = 10
SECONDS_PER_REVIEW = 20
SECONDS_PER_QUESTION = 60


@dataclass(frozen=True, slots=True)
class Budget:
    reviews: int
    questions: int
    lessons: int


BUDGETS: dict[int, Budget] = {
    5: Budget(reviews=6, questions=5, lessons=0),
    15: Budget(reviews=10, questions=8, lessons=0),
    30: Budget(reviews=15, questions=12, lessons=1),
}


def weakest_objectives(objectives: tuple[ObjectiveEvidence, ...]) -> tuple[ObjectiveEvidence, ...]:
    weak = [
        o
        for o in objectives
        if o.first_attempts >= MIN_EVIDENCE and (o.accuracy or 0.0) < WEAK_THRESHOLD
    ]
    weak.sort(key=lambda o: (o.accuracy or 0.0, -o.first_attempts, -o.domain_weight, o.code))
    return tuple(weak)


def plan_session(inp: PlannerInput) -> Plan:
    budget = BUDGETS.get(inp.minutes, BUDGETS[15])
    weakest = weakest_objectives(inp.objectives)

    if inp.active_session is not None:
        active = inp.active_session
        return Plan(
            minutes=inp.minutes,
            headline="Resume where you left off",
            blocks=(
                PlanBlock(
                    kind="resume",
                    count=active.total - active.answered,
                    label=f"Resume {active.kind} session",
                    reason=f"{active.answered} of {active.total} answered",
                    session_id=active.session_id,
                ),
            ),
            explanation=("An unfinished session always comes first; nothing is lost by resuming.",),
            weakest=weakest,
        )

    blocks: list[PlanBlock] = []
    explanation: list[str] = []

    review_cap = budget.reviews
    if inp.backlog_mode == "recovery":
        review_cap = min(review_cap, RECOVERY_REVIEW_CAP)
    review_count = min(inp.due_reviews, inp.reviews_remaining_today, review_cap)
    if review_count > 0:
        reason = f"{inp.due_reviews} card(s) due"
        if review_count < inp.due_reviews:
            reason += f"; showing {review_count} to fit the time and your daily limit"
        blocks.append(PlanBlock(kind="review", count=review_count, label="Review", reason=reason))
        explanation.append(f"Reviews first: {reason}.")

    question_count = min(budget.questions, inp.available_questions)
    if question_count > 0:
        if weakest:
            target = weakest[0]
            pct = round((target.accuracy or 0.0) * 100)
            focus = f"objective:{target.code}"
            reason = (
                f"objective {target.code} is your weakest: {target.first_correct}/"
                f"{target.first_attempts} first attempts ({pct}%)"
            )
            label = f"Practice objective {target.code}"
        else:
            focus = "mixed"
            evidence = sum(o.first_attempts for o in inp.objectives)
            reason = (
                "no objective has enough evidence yet, so a mixed set across domains finds gaps"
                if evidence < MIN_EVIDENCE * 2
                else "no objective is below the weak threshold, so a mixed set keeps coverage broad"
            )
            label = "Mixed practice"
        blocks.append(
            PlanBlock(
                kind="practice", count=question_count, label=label, reason=reason, focus=focus
            )
        )
        explanation.append(f"Practice: {reason}.")

    if budget.lessons and inp.next_lesson is not None:
        lesson = inp.next_lesson
        blocks.append(
            PlanBlock(
                kind="lesson",
                count=1,
                label=f"Read: {lesson.title}",
                reason=f"next unread lesson, about {lesson.estimated_minutes} min",
                item_key=lesson.item_key,
            )
        )
        explanation.append("A longer session leaves room for one lesson of new material.")

    if not blocks:
        return Plan(
            minutes=inp.minutes,
            headline="Nothing scheduled",
            blocks=(),
            explanation=("No due reviews and no practice questions available for this track.",),
            weakest=weakest,
        )

    headline = {
        "review": "Clear what is due, then practise",
        "practice": blocks[0].label,
    }.get(blocks[0].kind, "Study")
    return Plan(
        minutes=inp.minutes,
        headline=headline,
        blocks=tuple(blocks),
        explanation=tuple(explanation),
        weakest=weakest,
    )
