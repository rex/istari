"""Domain exceptions. Routes never raise HTTPException; `app.main` maps these."""

from __future__ import annotations


class IstariError(Exception):
    code = "error"
    status = 500

    def __init__(self, message: str, *, details: dict[str, object] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details: dict[str, object] = details or {}


class NotFoundError(IstariError):
    code = "not_found"
    status = 404


class ConflictError(IstariError):
    code = "conflict"
    status = 409


class ValidationError(IstariError):
    code = "validation_error"
    status = 422


class AuthenticationError(IstariError):
    code = "unauthenticated"
    status = 401


class ForbiddenError(IstariError):
    code = "forbidden"
    status = 403


class ThrottledError(IstariError):
    code = "throttled"
    status = 429
