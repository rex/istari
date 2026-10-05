"""Create and read study sessions. Answer handling lives in `answers.py`."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.adapters.db.models import Answer, ContentItem, ContentRevision, SessionItem, StudySession
from app.contracts.common import ObjectiveRef
from app.contracts.session import (
    ActiveSessionView,
    AnswerView,
    FeedbackView,
    OptionView,
    SessionItemView,
    SessionView,
)
from app.contracts.session_requests import SessionCreateRequest
from app.domain.exceptions import ConflictError, NotFoundError
from app.domain.grading import shuffle_option_ids
from app.domain.recommendation import BUDGETS
from app.services.content_query import (
    content_list,
    content_str,
    objective_refs,
    revision_sources,
)
from app.services.practice_select import select_questions

ItemRows = list[tuple[SessionItem, ContentItem, ContentRevision, Answer | None]]


async def get_active_session(db: AsyncSession) -> StudySession | None:
    return await db.scalar(
        select(StudySession)
        .where(StudySession.status == "in_progress")
        .order_by(StudySession.created_at.desc())
        .limit(1)
        .options(selectinload(StudySession.items))
    )


async def load_session(
    db: AsyncSession, session_id: int, *, for_update: bool = False
) -> StudySession:
    stmt = select(StudySession).where(StudySession.id == session_id)
    if for_update:
        stmt = stmt.with_for_update()
    session = await db.scalar(stmt)
    if session is None:
        raise NotFoundError("session not found")
    return session


async def load_item_rows(db: AsyncSession, session_id: int) -> ItemRows:
    rows = await db.execute(
        select(SessionItem, ContentItem, ContentRevision, Answer)
        .join(ContentItem, ContentItem.id == SessionItem.item_id)
        .join(ContentRevision, ContentRevision.id == SessionItem.revision_id)
        .outerjoin(Answer, Answer.session_item_id == SessionItem.id)
        .where(SessionItem.session_id == session_id)
        .order_by(SessionItem.position)
    )
    return [(si, item, rev, ans) for si, item, rev, ans in rows.all()]


async def create_session(
    db: AsyncSession,
    *,
    exam_version_id: int,
    req: SessionCreateRequest,
    now: datetime,
    objective_map: dict[str, ObjectiveRef],
    weak_focus: str | None,
) -> StudySession:
    active = await get_active_session(db)
    if active is not None:
        if not req.replace_active:
            raise ConflictError(
                "a session is already in progress", details={"session_id": active.id}
            )
        active.status = "abandoned"
        active.completed_at = now
        await db.flush()

    focus = req.focus
    if focus == "weak":
        focus = weak_focus or "mixed"
    count = BUDGETS.get(req.minutes, BUDGETS[15]).questions
    session = StudySession(
        exam_version_id=exam_version_id,
        kind=req.kind,
        focus=focus,
        planned_minutes=req.minutes,
        created_at=now,
        last_activity_at=now,
    )
    db.add(session)
    await db.flush()

    chosen, explanation = await select_questions(
        db,
        exam_version_id=exam_version_id,
        focus=focus,
        count=count,
        seed=session.id,
        objective_map=objective_map,
    )
    if not chosen:
        raise ConflictError("no usable questions are available for this track")
    for position, candidate in enumerate(chosen, start=1):
        option_ids = [
            str(o["id"]) for o in content_list(candidate.revision, "options") if isinstance(o, dict)
        ]
        db.add(
            SessionItem(
                session_id=session.id,
                position=position,
                item_id=candidate.item.id,
                revision_id=candidate.revision.id,
                option_order=shuffle_option_ids(option_ids, seed=session.id * 1000 + position),
            )
        )
    explanation["selected"] = [
        {"position": i + 1, "item_key": c.item.item_key, "group": c.group}
        for i, c in enumerate(chosen)
    ]
    session.explanation = explanation
    await db.flush()
    return session


def _feedback_view(
    revision: ContentRevision, answer: Answer | None, objective_map: dict[str, ObjectiveRef]
) -> FeedbackView:
    correct = [str(c) for c in content_list(revision, "correct_option_ids") if isinstance(c, str)]
    rationales = revision.content.get("distractor_rationales", {})
    selected = set(answer.selected_option_ids) if answer else set()
    return FeedbackView(
        correct_option_ids=correct,
        explanation_md=content_str(revision, "explanation_md"),
        distractor_rationales={str(k): str(v) for k, v in rationales.items()}
        if isinstance(rationales, dict)
        else {},
        decisive_constraint=content_str(revision, "decisive_constraint"),
        objectives=objective_refs(revision.objective_codes, objective_map),
        sources=revision_sources(revision),
        missed_option_ids=[c for c in correct if c not in selected],
        extra_option_ids=[
            s for s in (answer.selected_option_ids if answer else []) if s not in correct
        ],
    )


def item_view(
    si: SessionItem,
    item: ContentItem,
    revision: ContentRevision,
    answer: Answer | None,
    *,
    reveal: bool,
    objective_map: dict[str, ObjectiveRef],
) -> SessionItemView:
    options_by_id = {
        str(o["id"]): str(o.get("text_md", ""))
        for o in content_list(revision, "options")
        if isinstance(o, dict)
    }
    select_count = revision.content.get("select_count", 1)
    return SessionItemView(
        position=si.position,
        item_key=item.item_key,
        family_key=item.family_key,
        stem_md=content_str(revision, "stem_md"),
        select_count=int(select_count) if isinstance(select_count, int) else 1,
        difficulty=content_str(revision, "difficulty", "medium"),
        objectives=objective_refs(revision.objective_codes, objective_map),
        options=[
            OptionView(id=oid, text_md=options_by_id[oid])
            for oid in si.option_order
            if oid in options_by_id
        ],
        state="answered" if si.state == "answered" else "pending",
        draft_selection=list(si.draft_selection) if si.draft_selection is not None else None,
        draft_confidence=si.draft_confidence,  # type: ignore[arg-type]
        # Correctness stays hidden in an assessment until the session is completed.
        answer=AnswerView(
            selected_option_ids=list(answer.selected_option_ids),
            is_correct=answer.is_correct if reveal else None,
            confidence=answer.confidence,  # type: ignore[arg-type]
            first_attempt=answer.first_attempt,
            answered_at=answer.answered_at,
        )
        if answer is not None
        else None,
        feedback=_feedback_view(revision, answer, objective_map)
        if (answer is not None and reveal)
        else None,
    )


def feedback_visible(session: StudySession) -> bool:
    return session.kind == "practice" or session.status == "completed"


def session_view(
    session: StudySession, rows: ItemRows, objective_map: dict[str, ObjectiveRef]
) -> SessionView:
    reveal = feedback_visible(session)
    items = [
        item_view(si, item, rev, ans, reveal=reveal, objective_map=objective_map)
        for si, item, rev, ans in rows
    ]
    answers = [ans for _, _, _, ans in rows if ans is not None]
    return SessionView(
        id=session.id,
        kind=session.kind,  # type: ignore[arg-type]
        focus=session.focus,
        planned_minutes=session.planned_minutes,
        status=session.status,  # type: ignore[arg-type]
        version=session.version,
        created_at=session.created_at,
        completed_at=session.completed_at,
        answered_count=len(answers),
        correct_count=sum(1 for a in answers if a.is_correct) if reveal else None,
        total=len(rows),
        feedback_visible=reveal,
        explanation=dict(session.explanation),
        items=items,
    )


def active_view(session: StudySession, answered: int, total: int) -> ActiveSessionView:
    return ActiveSessionView(
        id=session.id,
        kind=session.kind,  # type: ignore[arg-type]
        answered_count=answered,
        total=total,
        planned_minutes=session.planned_minutes,
        created_at=session.created_at,
    )
