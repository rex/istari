"""The one error-body shape, for exception handlers and for routes that must
return an error *without* raising (so the request's transaction still commits)."""

from __future__ import annotations

from fastapi.responses import JSONResponse

from app.contracts.common import ErrorBody
from app.domain.exceptions import IstariError
from app.observability import request_id_var


def error_response(
    status: int, code: str, message: str, details: dict[str, object] | None = None
) -> JSONResponse:
    body = ErrorBody(
        error=code, message=message, details=details or {}, request_id=request_id_var.get()
    )
    return JSONResponse(status_code=status, content=body.model_dump())


def from_exception(exc: IstariError) -> JSONResponse:
    return error_response(exc.status, exc.code, exc.message, exc.details)
