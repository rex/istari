"""What a verifier backend tells us, as plain data. No HTTP, no framework.

The first backend is K16S (a real kubeadm cluster with an exam server): a session holds
one exam profile at a time, every question has a setup script and a validate script,
and the server reports pass or fail with the grader's own reason line.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

# Default length of a backend session when Istari has to start one (two hours, the exam's).
DEFAULT_SESSION_SECONDS = 7200


@dataclass(frozen=True, slots=True)
class VerifierQuestion:
    """A task as the backend describes it. Its text is shown live, never stored."""

    id: str
    title: str
    weight: int
    context: str = ""
    description: str = ""
    hint: str = ""
    # Empty means the task runs in every install mode; "heavy" needs the full VM install.
    requires: str = ""


@dataclass(frozen=True, slots=True)
class VerifierSession:
    id: str
    profile: str
    started_at: datetime | None = None
    ended_at: datetime | None = None
    duration_secs: int = DEFAULT_SESSION_SECONDS

    @property
    def active(self) -> bool:
        return self.ended_at is None


@dataclass(frozen=True, slots=True)
class VerifierStatus:
    ok: bool
    mode: str
    profiles: tuple[str, ...] = ()
    session: VerifierSession | None = None


@dataclass(frozen=True, slots=True)
class SetupResult:
    ok: bool
    output: str = ""
    # Set when the backend cannot create this task's environment in its current mode.
    unavailable_reason: str | None = None


@dataclass(frozen=True, slots=True)
class CheckResult:
    passed: bool
    output: str = ""
    unavailable_reason: str | None = None

    @property
    def reason_line(self) -> str:
        """The grader's one-line verdict: the last non-empty line of its output."""
        lines = [line.strip() for line in self.output.splitlines() if line.strip()]
        return lines[-1] if lines else ""


@dataclass(frozen=True, slots=True)
class StatusSnapshot:
    """The last thing we learned about the backend, for pages that must never wait on it."""

    checked_at: datetime
    status: VerifierStatus | None = None
    error: str | None = None

    @property
    def reachable(self) -> bool:
        return self.status is not None and self.status.ok


def cap_output(text: str, limit: int = 16_000) -> str:
    """Grader output is kept whole up to the limit, then cut with a marker, never silently."""
    if len(text) <= limit:
        return text
    return text[: limit - 24].rstrip() + "\n[output truncated]"
