"""Drafts, answers, completion. Transactional and idempotent by construction.

- `save_draft` carries an expected session version; a stale tab gets 409 with
  the current version instead of overwriting newer work.
- `submit_answer` locks the session row, grades on the server against the
  revision that was shown, and dedupes on both the session item (one answer
  each) and the client request id (retries). A race that slips past both
  checks hits a unique constraint inside a savepoint and resolves to the
  existing answer.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import exists, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import Answer, ContentItem, ContentRevision, SessionItem, StudySession
from app.contracts.common import ObjectiveRef
from app.contracts.session_requests import AnswerRequest, AnswerResponse, DraftRequest
from app.domain.exceptions import ConflictError, NotFoundError
from app.domain.grading import grade, normalize_selection, validate_cardinality
from app.services.content_query import content_list
from app.services.sessions import feedback_visible, item_view, load_item_rows, load_session


async def _load_item(
    db: AsyncSession, session_id: int, position: int
) -> tuple[SessionItem, ContentItem, ContentRevision]:
    row = (
        await db.execute(
            select(SessionItem, ContentItem, ContentRevision)
            .join(ContentItem, ContentItem.id == SessionItem.item_id)
            .join(ContentRevision, ContentRevision.id == SessionItem.revision_id)
            .where(SessionItem.session_id == session_id, SessionItem.position == position)
        )
    ).first()
    if row is None:
        raise NotFoundError("session item not found")
    return row[0], row[1], row[2]


def _require_open(session: StudySession) -> None:
    if session.status != "in_progress":
        raise ConflictError("session is closed", details={"status": session.status})


async def save_draft(
    db: AsyncSession, *, session_id: int, position: int, req: DraftRequest, now: datetime
) -> StudySession:
    session = await load_session(db, session_id, for_update=True)
    _require_open(session)
    if req.expected_version != session.version:
        raise ConflictError(
            "session changed in another tab; reload before editing",
            details={"current_version": session.version, "expected_version": req.expected_version},
        )
    si, _item, _rev = await _load_item(db, session_id, position)
    if si.state == "answered":
        raise ConflictError("item already answered")
    si.draft_selection = list(req.selected_option_ids)
    si.draft_confidence = req.confidence
    session.version += 1
    session.last_activity_at = now
    await db.flush()
    return session


async def submit_answer(
    db: AsyncSession,
    *,
    session_id: int,
    position: int,
    req: AnswerRequest,
    now: datetime,
    objective_map: dict[str, ObjectiveRef],
) -> AnswerResponse:
    session = await load_session(db, session_id, for_update=True)
    si, item, revision = await _load_item(db, session_id, position)

    existing = await db.scalar(
        select(Answer).where(
            (Answer.client_request_id == req.request_id) | (Answer.session_item_id == si.id)
        )
    )
    if existing is not None:
        if existing.session_item_id != si.id:
            raise ConflictError("request_id was already used for a different item")
        return await _response(db, session, si, item, revision, existing, True, objective_map)

    _require_open(session)
    option_ids = [str(o["id"]) for o in content_list(revision, "options") if isinstance(o, dict)]
    raw_count = revision.content.get("select_count", 1)
    select_count = raw_count if isinstance(raw_count, int) else 1
    selected = normalize_selection(req.selected_option_ids, option_ids)
    validate_cardinality(selected, select_count)
    correct = [str(c) for c in content_list(revision, "correct_option_ids") if isinstance(c, str)]
    result = grade(selected, correct)
    seen_before = await db.scalar(select(exists().where(Answer.family_key == item.family_key)))
    answer = Answer(
        session_item_id=si.id,
        session_id=session.id,
        item_id=item.id,
        revision_id=revision.id,
        family_key=item.family_key,
        session_kind=session.kind,
        selected_option_ids=list(selected),
        is_correct=result.is_correct,
        confidence=req.confidence,
        first_attempt=not bool(seen_before),
        client_request_id=req.request_id,
        answered_at=now,
    )
    try:
        async with db.begin_nested():
            db.add(answer)
            await db.flush()
    except IntegrityError:
        raced = await db.scalar(select(Answer).where(Answer.session_item_id == si.id))
        if raced is None:
            raise
        return await _response(db, session, si, item, revision, raced, True, objective_map)

    si.state = "answered"
    si.draft_selection = None
    si.draft_confidence = None
    session.version += 1
    session.last_activity_at = now
    await db.flush()
    return await _response(db, session, si, item, revision, answer, False, objective_map)


async def _response(
    db: AsyncSession,
    session: StudySession,
    si: SessionItem,
    item: ContentItem,
    revision: ContentRevision,
    answer: Answer,
    already: bool,
    objective_map: dict[str, ObjectiveRef],
) -> AnswerResponse:
    rows = await load_item_rows(db, session.id)
    answered_count = sum(1 for _, _, _, a in rows if a is not None)
    return AnswerResponse(
        item=item_view(
            si,
            item,
            revision,
            answer,
            reveal=feedback_visible(session),
            objective_map=objective_map,
        ),
        session_version=session.version,
        already_recorded=already,
        answered_count=answered_count,
        total=len(rows),
        status=session.status,  # type: ignore[arg-type]
    )


async def complete_session(db: AsyncSession, *, session_id: int, now: datetime) -> StudySession:
    session = await load_session(db, session_id, for_update=True)
    if session.status == "completed":
        return session
    _require_open(session)
    session.status = "completed"
    session.completed_at = now
    session.last_activity_at = now
    session.version += 1
    await db.flush()
    return session


async def abandon_session(db: AsyncSession, *, session_id: int, now: datetime) -> StudySession:
    session = await load_session(db, session_id, for_update=True)
    if session.status == "in_progress":
        session.status = "abandoned"
        session.completed_at = now
        session.version += 1
        await db.flush()
    return session
