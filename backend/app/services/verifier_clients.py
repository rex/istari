"""The verifier backends the app talks to, behind one interface: K16S and LocalEmu side by side.

A lab's spec names its backend; services look its client up here. A backend the owner has not
configured is simply absent from the mapping, and every caller reads that as "unconfigured".
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Protocol

from app.domain.planning_types import LabBackend
from app.domain.verifier import (
    CheckResult,
    SetupResult,
    StatusSnapshot,
    VerifierQuestion,
    VerifierSession,
    VerifierStatus,
)


class VerifierClient(Protocol):
    """What `K16sClient` and `LocalEmuClient` both offer. `run` is the attempt's backend run:
    LocalEmu names the attempt's resources after it; K16S keeps its session server-side."""

    # True when every setup makes a fresh run that its check must grade (LocalEmu); False when
    # the backend grades its one live session (K16S).
    per_attempt_runs: bool

    @property
    def terminal_url(self) -> str | None: ...

    @property
    def exam_url(self) -> str | None: ...

    @property
    def snapshot(self) -> StatusSnapshot | None: ...

    async def status(self) -> VerifierStatus: ...

    async def question(self, profile: str, question_id: str) -> VerifierQuestion | None: ...

    async def ensure_session(self, profile: str) -> VerifierSession: ...

    async def setup(self, question_id: str, *, run: str = "") -> SetupResult: ...

    async def check(self, question_id: str, *, run: str = "") -> CheckResult: ...

    def start_background_refresh(self) -> asyncio.Task[None]: ...

    async def aclose(self) -> None: ...


# Backend name (a pack verifier's `backend`) to its client; configured backends only.
VerifierClients = Mapping[str, VerifierClient]

# Per backend: where a lab's task text comes from, and what to set when the backend is missing.
_ATTRIBUTIONS = {
    "k16s": "Task text from K16S (PolyForm Noncommercial 1.0.0), fetched live from your instance.",
    "localemu": "Task text from Istari, graded against your LocalEmu AWS emulator.",
}
_UNCONFIGURED = {
    "k16s": "Verified labs are not configured: set K16S_BASE_URL to your K16S instance.",
    "localemu": "AWS labs are not configured: set LOCALEMU_BASE_URL to your LocalEmu emulator.",
}


def attribution(backend: str) -> str:
    return _ATTRIBUTIONS.get(backend, "")


def unconfigured_message(backend: str) -> str:
    return _UNCONFIGURED.get(backend, f"The '{backend}' verifier backend is not configured.")


def backend_state(client: VerifierClient | None) -> LabBackend:
    """From the client's background snapshot only: the planner never waits on a backend."""
    if client is None:
        return "unconfigured"
    snapshot = client.snapshot
    return "ready" if snapshot is not None and snapshot.reachable else "unreachable"
