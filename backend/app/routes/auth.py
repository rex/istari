"""Login, logout, and the `/api/me` bootstrap payload."""

from __future__ import annotations

from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse

from app.adapters.db.models import Certification
from app.config import settings
from app.contracts.auth import LoginRequest, MeView, UserView
from app.contracts.common import ErrorBody, OkResponse
from app.deps import ClockDep, DbSession, Protected, SettingsDep
from app.domain.exceptions import AuthenticationError
from app.routes.errors import from_exception
from app.services import auth as auth_service
from app.services.settings import settings_view
from app.services.track import active_track, list_tracks, track_summary

router = APIRouter()


def _set_cookie(response: Response, raw_token: str) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=raw_token,
        max_age=settings.session_ttl_hours * 3600,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )


@router.post("/auth/login", response_model=UserView, responses={401: {"model": ErrorBody}})
async def login(payload: LoginRequest, db: DbSession, clock: ClockDep) -> JSONResponse:
    try:
        session, raw = await auth_service.login(
            db, payload.username, payload.password, now=clock.now(), cfg=settings
        )
    except AuthenticationError as exc:
        # Returned, not raised: the failed attempt must commit so throttling counts it.
        return from_exception(exc)
    owner = await auth_service.get_owner(db)
    view = UserView(
        username=owner.username if owner else payload.username, csrf_token=session.csrf_token
    )
    response = JSONResponse(content=view.model_dump())
    _set_cookie(response, raw)
    return response


@router.post("/auth/logout", response_model=OkResponse)
async def logout(
    session: Protected, response: Response, db: DbSession, clock: ClockDep
) -> OkResponse:
    await auth_service.logout(db, session, now=clock.now())
    response.delete_cookie(settings.session_cookie_name, path="/")
    return OkResponse()


@router.get("/me", response_model=MeView)
async def me(session: Protected, db: DbSession, user_settings: SettingsDep) -> MeView:
    owner = await auth_service.get_owner(db)
    exam = await active_track(db, user_settings)
    track = None
    if exam is not None:
        cert = await db.get(Certification, exam.certification_id)
        if cert is not None:
            track = track_summary(exam, cert)
    return MeView(
        user=UserView(username=owner.username if owner else "owner", csrf_token=session.csrf_token),
        settings=settings_view(user_settings),
        track=track,
        available_tracks=await list_tracks(db),
        onboarding_required=user_settings.onboarding_completed_at is None or track is None,
    )
