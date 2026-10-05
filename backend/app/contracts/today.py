"""The Today screen: one recommendation, explained."""

from __future__ import annotations

from datetime import date

from app.contracts.common import ApiModel
from app.contracts.session import ActiveSessionView


class PlanBlockView(ApiModel):
    kind: str
    count: int
    label: str
    reason: str
    focus: str | None
    session_id: int | None
    item_key: str | None


class WeakObjectiveView(ApiModel):
    code: str
    title: str
    first_attempts: int
    first_correct: int
    accuracy: float | None


class RecentView(ApiModel):
    answers_7d: int
    reviews_7d: int
    lessons_completed: int
    lessons_total: int
    last_study_date: date | None


class ExamView(ApiModel):
    code: str
    name: str
    exam_date: date | None
    days_left: int | None


class TodayView(ApiModel):
    minutes: int
    headline: str
    blocks: list[PlanBlockView]
    explanation: list[str]
    active_session: ActiveSessionView | None
    due_reviews: int
    reviews_remaining_today: int
    weakest: list[WeakObjectiveView]
    recent: RecentView
    exam: ExamView | None
    quiet_win: str | None
