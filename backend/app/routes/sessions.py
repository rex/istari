"""Study sessions: create, read, draft, answer, complete, abandon."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.contracts.session import ActiveSessionView, SessionView
from app.contracts.session_requests import (
    AnswerRequest,
    AnswerResponse,
    DraftRequest,
    SessionCreateRequest,
)
from app.deps import ActiveExam, ClockDep, DbSession, ObjectiveMap, require_auth
from app.services import answers as answer_service
from app.services import sessions as session_service
from app.services.today import objective_evidence, weak_focus

router = APIRouter(dependencies=[Depends(require_auth)])


async def _view(db: DbSession, session_id: int, objective_map: ObjectiveMap) -> SessionView:
    session = await session_service.load_session(db, session_id)
    rows = await session_service.load_item_rows(db, session.id)
    return session_service.session_view(session, rows, objective_map)


@router.post("", response_model=SessionView, status_code=status.HTTP_201_CREATED)
async def create(
    req: SessionCreateRequest,
    db: DbSession,
    clock: ClockDep,
    exam: ActiveExam,
    objective_map: ObjectiveMap,
) -> SessionView:
    focus = weak_focus(await objective_evidence(db, exam.id)) if req.focus == "weak" else None
    session = await session_service.create_session(
        db,
        exam_version_id=exam.id,
        req=req,
        now=clock.now(),
        objective_map=objective_map,
        weak_focus=focus,
    )
    return await _view(db, session.id, objective_map)


@router.get("/active", response_model=ActiveSessionView | None)
async def active(db: DbSession) -> ActiveSessionView | None:
    session = await session_service.get_active_session(db)
    if session is None:
        return None
    rows = await session_service.load_item_rows(db, session.id)
    return session_service.active_view(session, sum(1 for *_, a in rows if a), len(rows))


@router.get("/{session_id}", response_model=SessionView)
async def read(session_id: int, db: DbSession, objective_map: ObjectiveMap) -> SessionView:
    return await _view(db, session_id, objective_map)


@router.put("/{session_id}/items/{position}/draft", response_model=SessionView)
async def draft(
    session_id: int,
    position: int,
    req: DraftRequest,
    db: DbSession,
    clock: ClockDep,
    objective_map: ObjectiveMap,
) -> SessionView:
    await answer_service.save_draft(
        db, session_id=session_id, position=position, req=req, now=clock.now()
    )
    return await _view(db, session_id, objective_map)


@router.post("/{session_id}/items/{position}/answer", response_model=AnswerResponse)
async def answer(
    session_id: int,
    position: int,
    req: AnswerRequest,
    db: DbSession,
    clock: ClockDep,
    objective_map: ObjectiveMap,
) -> AnswerResponse:
    return await answer_service.submit_answer(
        db,
        session_id=session_id,
        position=position,
        req=req,
        now=clock.now(),
        objective_map=objective_map,
    )


@router.post("/{session_id}/complete", response_model=SessionView)
async def complete(
    session_id: int, db: DbSession, clock: ClockDep, objective_map: ObjectiveMap
) -> SessionView:
    await answer_service.complete_session(db, session_id=session_id, now=clock.now())
    return await _view(db, session_id, objective_map)


@router.post("/{session_id}/abandon", response_model=SessionView)
async def abandon(
    session_id: int, db: DbSession, clock: ClockDep, objective_map: ObjectiveMap
) -> SessionView:
    await answer_service.abandon_session(db, session_id=session_id, now=clock.now())
    return await _view(db, session_id, objective_map)
