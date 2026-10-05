"""FastAPI dependencies: db session, clock, auth + CSRF, settings, active track."""

from __future__ import annotations

import secrets
from collections.abc import AsyncIterator
from typing import Annotated
from urllib.parse import urlsplit

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.adapters.db.models import AuthSession, ExamVersion, UserSettings
from app.config import settings
from app.contracts.common import ObjectiveRef
from app.domain.clock import Clock
from app.domain.exceptions import AuthenticationError, ConflictError, ForbiddenError
from app.services import auth as auth_service
from app.services.content_query import load_objective_map
from app.services.settings import get_settings
from app.services.track import active_track

_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    """One transaction per request: commit on success, rollback on any exception."""
    factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    async with factory() as session, session.begin():
        yield session


def get_clock(request: Request) -> Clock:
    clock: Clock = request.app.state.clock
    return clock


DbSession = Annotated[AsyncSession, Depends(get_db_session)]
ClockDep = Annotated[Clock, Depends(get_clock)]


async def get_current_session(request: Request, db: DbSession, clock: ClockDep) -> AuthSession:
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        raise AuthenticationError("login required")
    session = await auth_service.authenticate(db, token, now=clock.now())
    if session is None:
        raise AuthenticationError("session expired; log in again")
    return session


CurrentSession = Annotated[AuthSession, Depends(get_current_session)]


async def require_auth(request: Request, session: CurrentSession) -> AuthSession:
    """Auth for every method; synchronizer-token CSRF + Origin check for unsafe ones."""
    if request.method in _SAFE_METHODS:
        return session
    header = request.headers.get("x-csrf-token", "")
    if not header or not secrets.compare_digest(header, session.csrf_token):
        raise ForbiddenError("missing or invalid CSRF token")
    origin = request.headers.get("origin")
    host = request.headers.get("host", "")
    if origin and urlsplit(origin).netloc != host:
        raise ForbiddenError("cross-origin request rejected")
    return session


Protected = Annotated[AuthSession, Depends(require_auth)]


async def get_user_settings(db: DbSession) -> UserSettings:
    return await get_settings(db)


SettingsDep = Annotated[UserSettings, Depends(get_user_settings)]


async def get_active_exam(db: DbSession, user_settings: SettingsDep) -> ExamVersion:
    exam = await active_track(db, user_settings)
    if exam is None:
        raise ConflictError(
            "no active track; complete onboarding first", details={"code": "onboarding"}
        )
    return exam


ActiveExam = Annotated[ExamVersion, Depends(get_active_exam)]


async def get_objective_map(db: DbSession, exam: ActiveExam) -> dict[str, ObjectiveRef]:
    return await load_objective_map(db, exam.id)


ObjectiveMap = Annotated[dict[str, ObjectiveRef], Depends(get_objective_map)]
