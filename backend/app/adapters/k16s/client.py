"""The K16S REST API, as Istari uses it. Contract in docs/labs-k16s.md.

Every call maps to plain domain data; every failure to talk to the server becomes an
`UpstreamError` with a sentence an owner can act on. The client keeps two small caches so
the pages that must stay fast never wait on the cluster: the question list per profile
(60 s) and a status snapshot that `/api/health` and the planner read without I/O.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx

from app.domain.exceptions import UpstreamError
from app.domain.verifier import (
    DEFAULT_SESSION_SECONDS,
    CheckResult,
    SetupResult,
    StatusSnapshot,
    VerifierQuestion,
    VerifierSession,
    VerifierStatus,
)

log = logging.getLogger("istari.k16s")

QUESTION_CACHE_SECONDS = 60
STATUS_REFRESH_SECONDS = 60


@dataclass(frozen=True, slots=True)
class K16sTimeouts:
    """Seconds. K16S enforces 60 s on setup and 30 s on check server-side; ours are longer."""

    read: float = 10.0
    setup: float = 90.0
    check: float = 45.0


DEFAULT_TIMEOUTS = K16sTimeouts()


class K16sClient:
    # One live session on the server, which every check grades.
    per_attempt_runs = False

    def __init__(
        self,
        base_url: str,
        *,
        public_url: str = "",
        http: httpx.AsyncClient | None = None,
        timeouts: K16sTimeouts = DEFAULT_TIMEOUTS,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.public_url = (public_url or base_url).rstrip("/")
        self.timeouts = timeouts
        self._http = http or httpx.AsyncClient(timeout=timeouts.read)
        self._questions: dict[str, tuple[datetime, list[VerifierQuestion]]] = {}
        self._snapshot: StatusSnapshot | None = None
        self._refresh_task: asyncio.Task[None] | None = None

    # ── URLs the browser opens ────────────────────────────────────────────
    @property
    def terminal_url(self) -> str:
        return f"{self.public_url}/terminal/"

    @property
    def exam_url(self) -> str:
        return f"{self.public_url}/"

    @property
    def cli_env(self) -> tuple[str, ...]:
        """Nothing: the work happens in K16S's own terminal."""
        return ()

    # ── Lifecycle ─────────────────────────────────────────────────────────
    async def aclose(self) -> None:
        if self._refresh_task is not None:
            self._refresh_task.cancel()
        await self._http.aclose()

    def start_background_refresh(self) -> asyncio.Task[None]:
        """Keep the status snapshot fresh so health and the planner never block on the cluster."""

        async def loop() -> None:
            while True:
                await self.refresh_snapshot()
                await asyncio.sleep(STATUS_REFRESH_SECONDS)

        self._refresh_task = asyncio.create_task(loop())
        return self._refresh_task

    # ── Status ────────────────────────────────────────────────────────────
    @property
    def snapshot(self) -> StatusSnapshot | None:
        return self._snapshot

    async def refresh_snapshot(self) -> StatusSnapshot:
        now = datetime.now(UTC)
        try:
            status = await self.status()
            self._snapshot = StatusSnapshot(checked_at=now, status=status)
        except UpstreamError as exc:
            self._snapshot = StatusSnapshot(checked_at=now, error=exc.message)
        return self._snapshot

    async def status(self) -> VerifierStatus:
        data = await self._request("GET", "/api/status", wait_seconds=self.timeouts.read)
        session = data.get("session")
        return VerifierStatus(
            ok=bool(data.get("ok", False)),
            mode=str(data.get("mode", "")),
            profiles=tuple(sorted(str(p) for p in _as_list(data.get("profiles")))),
            session=_session(session) if isinstance(session, dict) else None,
        )

    # ── Questions ─────────────────────────────────────────────────────────
    async def questions(self, profile: str) -> list[VerifierQuestion]:
        cached = self._questions.get(profile)
        now = datetime.now(UTC)
        if cached is not None and now - cached[0] < timedelta(seconds=QUESTION_CACHE_SECONDS):
            return cached[1]
        data = await self._request(
            "GET", "/api/questions", params={"profile": profile}, wait_seconds=self.timeouts.read
        )
        questions = [_question(q) for q in _as_list(data.get("questions")) if isinstance(q, dict)]
        self._questions[profile] = (now, questions)
        return questions

    async def question(self, profile: str, question_id: str) -> VerifierQuestion | None:
        return next((q for q in await self.questions(profile) if q.id == question_id), None)

    # ── Sessions ──────────────────────────────────────────────────────────
    async def ensure_session(
        self, profile: str, duration_secs: int = DEFAULT_SESSION_SECONDS
    ) -> VerifierSession:
        """Reuse the active session when it is on this profile; otherwise start one.

        K16S allows one session; starting another ends the previous one, so a switch is
        deliberate and only happens when a lab needs a different profile.
        """
        status = await self.status()
        current = status.session
        if current is not None and current.active and current.profile == profile:
            return current
        data = await self._request(
            "POST",
            "/api/session/start",
            json={"profile": profile, "duration_secs": duration_secs},
            wait_seconds=self.timeouts.read,
        )
        session = data.get("session")
        if not isinstance(session, dict):
            raise UpstreamError(f"K16S at {self.base_url} started a session but returned none")
        log.info(
            "k16s session started",
            extra={"event": "k16s.session", "profile": profile, "switched": current is not None},
        )
        return _session(session)

    # ── Setup and check ───────────────────────────────────────────────────
    # `run` is the attempt's backend run; K16S keeps its own session server-side, so it is
    # accepted for the shared verifier surface and not sent.
    async def setup(self, question_id: str, *, run: str = "") -> SetupResult:
        data = await self._request(
            "POST", f"/api/questions/{question_id}/setup", wait_seconds=self.timeouts.setup
        )
        if data.get("unavailable"):
            return SetupResult(ok=False, unavailable_reason=str(data.get("reason", "")))
        return SetupResult(ok=bool(data.get("ok", False)), output=str(data.get("output", "")))

    async def check(self, question_id: str, *, run: str = "") -> CheckResult:
        data = await self._request(
            "POST", f"/api/questions/{question_id}/check", wait_seconds=self.timeouts.check
        )
        if data.get("unavailable"):
            return CheckResult(passed=False, unavailable_reason=str(data.get("reason", "")))
        return CheckResult(
            passed=bool(data.get("passed", False)), output=str(data.get("output", ""))
        )

    # ── Transport ─────────────────────────────────────────────────────────
    async def _request(
        self,
        method: str,
        path: str,
        *,
        wait_seconds: float,
        params: dict[str, str] | None = None,
        json: dict[str, object] | None = None,
    ) -> dict[str, object]:
        url = f"{self.base_url}{path}"
        try:
            response = await self._http.request(
                method, url, params=params, json=json, timeout=wait_seconds
            )
        except httpx.TimeoutException as exc:
            raise UpstreamError(
                f"K16S at {self.base_url} did not answer within {wait_seconds:g} s"
            ) from exc
        except httpx.HTTPError as exc:
            raise UpstreamError(f"K16S at {self.base_url} is not reachable: {exc}") from exc
        if response.status_code >= 400:
            raise UpstreamError(
                f"K16S at {self.base_url} answered {response.status_code} for {method} {path}: "
                f"{_error_text(response)}",
                details={"status": response.status_code, "path": path},
            )
        try:
            body = response.json()
        except ValueError as exc:
            raise UpstreamError(f"K16S at {self.base_url} returned a non-JSON body") from exc
        if not isinstance(body, dict):
            raise UpstreamError(f"K16S at {self.base_url} returned an unexpected body")
        return body


def _as_list(value: object) -> list[object]:
    return list(value) if isinstance(value, list) else []


def _error_text(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return response.text[:200]
    if isinstance(body, dict) and "error" in body:
        return str(body["error"])
    return response.text[:200]


def _timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _session(data: dict[str, object]) -> VerifierSession:
    duration = data.get("duration_secs", DEFAULT_SESSION_SECONDS)
    return VerifierSession(
        id=str(data.get("id", "")),
        profile=str(data.get("profile", "")),
        started_at=_timestamp(data.get("started_at")),
        ended_at=_timestamp(data.get("ended_at")),
        duration_secs=int(duration) if isinstance(duration, int) else DEFAULT_SESSION_SECONDS,
    )


def _question(data: dict[str, object]) -> VerifierQuestion:
    weight = data.get("weight", 1)
    return VerifierQuestion(
        id=str(data.get("id", "")),
        title=str(data.get("title", "")),
        weight=int(weight) if isinstance(weight, int) else 1,
        context=str(data.get("context", "") or ""),
        description=str(data.get("description", "") or ""),
        hint=str(data.get("hint", "") or ""),
        requires=str(data.get("requires", "") or ""),
    )
