"""`/api/health` body: liveness, database reachability, and the build that is running."""

from __future__ import annotations

from typing import Literal

from app.contracts.common import ApiModel

HealthStatus = Literal["ok", "unhealthy"]


class HealthView(ApiModel):
    status: HealthStatus
    reason: str | None = None
    version: str
    # Short git hash, or "unknown" outside a checkout without GIT_COMMIT set.
    commit: str
    # ISO-8601 build timestamp from the image; None in development.
    built_at: str | None
    # When this process started: the closest thing to a deployment time.
    started_at: str
