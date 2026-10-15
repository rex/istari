"""`/api/health` body: liveness, database reachability, and the build that is running."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.contracts.common import ApiModel

HealthStatus = Literal["ok", "unhealthy"]


class K16sHealth(ApiModel):
    """The verified-labs backend, from the last background poll: never a live call here."""

    configured: bool
    # None until the first poll has answered.
    reachable: bool | None = None
    mode: str | None = None
    profiles: list[str] = Field(default_factory=list)
    checked_at: str | None = None


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
    k16s: K16sHealth
