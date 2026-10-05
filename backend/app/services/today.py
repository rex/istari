"""Assemble the Today recommendation from live data, then let the planner decide."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import (
    Answer,
    ContentItem,
    ContentItemObjective,
    ContentPack,
    ContentRevision,
    Domain,
    ExamVersion,
    ItemProgress,
    Objective,
    ReviewEvent,
    UserSettings,
)
from app.contracts.common import ObjectiveRef
from app.contracts.today import ExamView, PlanBlockView, RecentView, TodayView, WeakObjectiveView
from app.domain.planning_types import ActiveSession, ObjectiveEvidence, Plan, PlannerInput
from app.domain.recommendation import plan_session, weakest_objectives
from app.domain.timeframes import days_until, local_date
from app.services.content_query import USABLE_REVIEW_STATUSES
from app.services.lessons import next_unread_lesson
from app.services.reviews import due_count, reviewed_today
from app.services.sessions import active_view, get_active_session, load_item_rows


async def objective_evidence(
    db: AsyncSession, exam_version_id: int
) -> tuple[ObjectiveEvidence, ...]:
    """Per objective: first-attempt answers (active items only) and usable question count."""
    usable = (
        select(ContentItem.id)
        .join(ContentRevision, ContentRevision.item_id == ContentItem.id)
        .join(ContentPack, ContentPack.id == ContentItem.pack_id)
        .where(
            ContentPack.exam_version_id == exam_version_id,
            ContentItem.kind == "question",
            ContentItem.status == "active",
            ContentRevision.is_current.is_(True),
            (ContentRevision.review_status.in_(USABLE_REVIEW_STATUSES))
            | (ContentItem.user_approved.is_(True)),
        )
        .subquery()
    )
    questions = (
        select(ContentItemObjective.objective_id, func.count().label("n"))
        .join(usable, usable.c.id == ContentItemObjective.item_id)
        .group_by(ContentItemObjective.objective_id)
        .subquery()
    )
    attempts = (
        select(
            ContentItemObjective.objective_id,
            func.count(Answer.id).label("attempts"),
            func.sum(case((Answer.is_correct.is_(True), 1), else_=0)).label("correct"),
        )
        .join(Answer, Answer.item_id == ContentItemObjective.item_id)
        .join(ContentItem, ContentItem.id == Answer.item_id)
        .where(Answer.first_attempt.is_(True), ContentItem.status == "active")
        .group_by(ContentItemObjective.objective_id)
        .subquery()
    )
    rows = await db.execute(
        select(
            Objective.code,
            Objective.title,
            Domain.weight_percent,
            func.coalesce(attempts.c.attempts, 0),
            func.coalesce(attempts.c.correct, 0),
            func.coalesce(questions.c.n, 0),
        )
        .join(Domain, Domain.id == Objective.domain_id)
        .outerjoin(attempts, attempts.c.objective_id == Objective.id)
        .outerjoin(questions, questions.c.objective_id == Objective.id)
        .where(Domain.exam_version_id == exam_version_id)
        .order_by(Domain.position, Objective.position)
    )
    return tuple(
        ObjectiveEvidence(
            code=code,
            title=title,
            domain_weight=int(weight),
            first_attempts=int(n_attempts),
            first_correct=int(n_correct),
            available_questions=int(n_questions),
        )
        for code, title, weight, n_attempts, n_correct, n_questions in rows.all()
    )


async def build_plan(
    db: AsyncSession,
    *,
    settings: UserSettings,
    exam: ExamVersion,
    now: datetime,
    minutes: int,
    objective_map: dict[str, ObjectiveRef],
) -> tuple[Plan, ActiveSession | None]:
    active_row = await get_active_session(db)
    active: ActiveSession | None = None
    if active_row is not None:
        rows = await load_item_rows(db, active_row.id)
        active = ActiveSession(
            session_id=active_row.id,
            kind=active_row.kind,
            answered=sum(1 for *_, a in rows if a is not None),
            total=len(rows),
        )
    evidence = await objective_evidence(db, exam.id)
    done_today = await reviewed_today(db, now=now, tz=settings.timezone)
    plan = plan_session(
        PlannerInput(
            minutes=minutes,
            active_session=active,
            due_reviews=await due_count(db, now=now),
            reviews_remaining_today=max(settings.daily_review_limit - done_today, 0),
            backlog_mode=settings.backlog_mode,
            objectives=evidence,
            available_questions=await usable_question_count(db, exam.id),
            next_lesson=await next_unread_lesson(
                db, exam_version_id=exam.id, settings=settings, objective_map=objective_map
            ),
        )
    )
    return plan, active


async def usable_question_count(db: AsyncSession, exam_version_id: int) -> int:
    """Active, source-checked (or user-approved) questions for the track."""
    count = await db.scalar(
        select(func.count(ContentItem.id))
        .join(ContentRevision, ContentRevision.item_id == ContentItem.id)
        .join(ContentPack, ContentPack.id == ContentItem.pack_id)
        .where(
            ContentPack.exam_version_id == exam_version_id,
            ContentItem.kind == "question",
            ContentItem.status == "active",
            ContentRevision.is_current.is_(True),
            (ContentRevision.review_status.in_(USABLE_REVIEW_STATUSES))
            | (ContentItem.user_approved.is_(True)),
        )
    )
    return int(count or 0)


def weak_focus(evidence: tuple[ObjectiveEvidence, ...]) -> str | None:
    weakest = weakest_objectives(evidence)
    return f"objective:{weakest[0].code}" if weakest else None


def block_view(block: object) -> PlanBlockView:
    return PlanBlockView.model_validate(block, from_attributes=True)


async def _recent(db: AsyncSession, *, exam: ExamVersion, now: datetime, tz: str) -> RecentView:
    week_ago = now - timedelta(days=7)
    answers = await db.scalar(select(func.count(Answer.id)).where(Answer.answered_at >= week_ago))
    reviews = await db.scalar(
        select(func.count(ReviewEvent.id)).where(ReviewEvent.reviewed_at >= week_ago)
    )
    lessons_total = await db.scalar(
        select(func.count(ContentItem.id))
        .join(ContentPack, ContentPack.id == ContentItem.pack_id)
        .where(
            ContentPack.exam_version_id == exam.id,
            ContentItem.kind == "lesson",
            ContentItem.status == "active",
        )
    )
    lessons_done = await db.scalar(
        select(func.count(ItemProgress.id))
        .join(ContentItem, ContentItem.id == ItemProgress.item_id)
        .where(ContentItem.kind == "lesson", ItemProgress.completed_at.is_not(None))
    )
    last_answer = await db.scalar(select(func.max(Answer.answered_at)))
    last_review = await db.scalar(select(func.max(ReviewEvent.reviewed_at)))
    stamps = [s for s in (last_answer, last_review) if s is not None]
    return RecentView(
        answers_7d=int(answers or 0),
        reviews_7d=int(reviews or 0),
        lessons_completed=int(lessons_done or 0),
        lessons_total=int(lessons_total or 0),
        last_study_date=local_date(max(stamps), tz) if stamps else None,
    )


def _quiet_win(recent: RecentView) -> str | None:
    if recent.answers_7d >= 20:
        return f"{recent.answers_7d} questions answered this week."
    if recent.reviews_7d >= 20:
        return f"{recent.reviews_7d} cards reviewed this week."
    if recent.lessons_completed and recent.lessons_completed == recent.lessons_total:
        return "Every lesson in this track has been read at least once."
    if recent.answers_7d or recent.reviews_7d:
        return "Studied this week. That is the whole trick."
    return None


async def build_today(
    db: AsyncSession,
    *,
    settings: UserSettings,
    exam: ExamVersion,
    now: datetime,
    minutes: int,
    objective_map: dict[str, ObjectiveRef],
) -> TodayView:
    plan, active = await build_plan(
        db, settings=settings, exam=exam, now=now, minutes=minutes, objective_map=objective_map
    )
    recent = await _recent(db, exam=exam, now=now, tz=settings.timezone)
    done_today = await reviewed_today(db, now=now, tz=settings.timezone)
    active_row = await get_active_session(db) if active else None
    return TodayView(
        minutes=minutes,
        headline=plan.headline,
        blocks=[block_view(b) for b in plan.blocks],
        explanation=list(plan.explanation),
        active_session=active_view(active_row, active.answered, active.total)
        if active_row is not None and active is not None
        else None,
        due_reviews=await due_count(db, now=now),
        reviews_remaining_today=max(settings.daily_review_limit - done_today, 0),
        weakest=[
            WeakObjectiveView(
                code=o.code,
                title=o.title,
                first_attempts=o.first_attempts,
                first_correct=o.first_correct,
                accuracy=o.accuracy,
            )
            for o in plan.weakest[:3]
        ],
        recent=recent,
        exam=ExamView(
            code=exam.code,
            name=exam.name,
            exam_date=settings.exam_date,
            days_left=days_until(settings.exam_date, now, settings.timezone)
            if settings.exam_date
            else None,
        ),
        quiet_win=_quiet_win(recent),
    )
