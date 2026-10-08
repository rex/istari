"""App factory: lifespan, middleware, exception mapping, routers, SPA mount."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import anyio
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncEngine

from app.adapters.db.engine import create_engine, dispose_engine
from app.adapters.db.session import session_factory
from app.buildinfo import load_build_info
from app.config import settings
from app.contracts.common import ErrorBody
from app.domain.clock import Clock, SystemClock
from app.domain.exceptions import IstariError
from app.observability import (
    RequestIdMiddleware,
    SecurityHeadersMiddleware,
    configure_logging,
    request_id_var,
)
from app.routes import (
    auth,
    content,
    health,
    labs,
    lessons,
    notes,
    progress,
    reviews,
    sessions,
    settings_routes,
    today,
    track,
)

log = logging.getLogger("istari.app")


def _error(
    status: int, code: str, message: str, details: dict[str, object] | None = None
) -> JSONResponse:
    body = ErrorBody(
        error=code, message=message, details=details or {}, request_id=request_id_var.get()
    )
    return JSONResponse(status_code=status, content=body.model_dump())


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(IstariError)
    async def domain_error(_request: Request, exc: IstariError) -> JSONResponse:
        return _error(exc.status, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(_request: Request, exc: RequestValidationError) -> JSONResponse:
        issues = [
            {"loc": ".".join(str(p) for p in e["loc"]), "msg": e["msg"]} for e in exc.errors()
        ]
        return _error(422, "invalid_request", "request failed validation", {"issues": issues})

    @app.exception_handler(Exception)
    async def unhandled(_request: Request, exc: Exception) -> JSONResponse:
        log.error("unhandled error", exc_info=exc)
        return _error(
            500, "internal_error", "something went wrong; the request id is in the response"
        )


def _mount_spa(app: FastAPI, static_dir: Path) -> None:
    """Serve the built SPA from the API origin: hashed assets cached, index.html never."""
    assets = static_dir / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")
    index = static_dir / "index.html"
    root = static_dir.resolve()

    def resolve_static(full_path: str) -> Path | None:
        candidate = (root / full_path).resolve()
        if full_path and candidate.is_relative_to(root) and candidate.is_file():
            return candidate
        return None

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str) -> FileResponse:
        candidate = await anyio.to_thread.run_sync(resolve_static, full_path)
        if candidate is not None:
            return FileResponse(candidate)
        return FileResponse(index, headers={"Cache-Control": "no-cache"})


def create_app(*, engine: AsyncEngine | None = None, clock: Clock | None = None) -> FastAPI:
    owns_engine = engine is None

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if app.state.engine is None:
            app.state.engine = create_engine(settings.database_url)
            app.state.session_factory = session_factory(app.state.engine)
        try:
            yield
        finally:
            if owns_engine and app.state.engine is not None:
                await dispose_engine(app.state.engine)

    configure_logging(settings.log_level)
    build_info = load_build_info(commit=settings.git_commit, build_date=settings.build_date)
    log.info(
        "istari %s (%s, built %s) starting",
        build_info.version,
        build_info.commit,
        build_info.built_at or "in development",
    )
    app = FastAPI(
        title=settings.service_name,
        version=build_info.version,
        lifespan=lifespan,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
    )
    app.state.build_info = build_info
    app.state.engine = engine
    app.state.session_factory = session_factory(engine) if engine is not None else None
    app.state.clock = clock or SystemClock()
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestIdMiddleware)

    app.include_router(health.router, prefix="/api", tags=["health"])
    app.include_router(auth.router, prefix="/api", tags=["auth"])
    app.include_router(settings_routes.router, prefix="/api", tags=["settings"])
    app.include_router(track.router, prefix="/api", tags=["track"])
    app.include_router(today.router, prefix="/api", tags=["today"])
    app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])
    app.include_router(lessons.router, prefix="/api/lessons", tags=["lessons"])
    app.include_router(notes.router, prefix="/api/notes", tags=["notes"])
    app.include_router(reviews.router, prefix="/api/reviews", tags=["reviews"])
    app.include_router(progress.router, prefix="/api", tags=["progress"])
    app.include_router(content.router, prefix="/api/content", tags=["content"])
    app.include_router(labs.router, prefix="/api/labs", tags=["labs"])
    register_exception_handlers(app)

    static_dir = Path(settings.static_dir)
    if (static_dir / "index.html").is_file():
        _mount_spa(app, static_dir)
    return app


app = create_app()
