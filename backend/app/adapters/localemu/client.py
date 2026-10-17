"""The LocalEmu AWS emulator as a verifier backend, with the K16S client's surface.

Status is one HTTP GET on the emulator's health endpoint; questions come from Istari's own
scenario registry; setup, check and teardown run a scenario's boto3 calls off the event loop.
Every failure to talk to the emulator becomes an `UpstreamError` with a sentence an owner can
act on, and the background snapshot lets health and the planner read the emulator's state
without waiting on it, exactly as they do for K16S.
"""

from __future__ import annotations

import asyncio
import logging
import secrets
from collections.abc import Callable
from datetime import UTC, datetime
from typing import TypeVar

import anyio
import httpx

from app.adapters.localemu.aws import (
    AWS_ERRORS,
    DEFAULT_TIMEOUTS,
    UNCHECKED_SIGNING_KEY,
    Aws,
    LocalEmuTimeouts,
    emulator_aws,
    emulator_endpoint,
    upstream_error,
)
from app.adapters.localemu.scenario import Scenario, ScenarioContext, ScenarioRegistry
from app.adapters.localemu.scenarios import REGISTRY
from app.domain.exceptions import UpstreamError
from app.domain.verifier import (
    CheckResult,
    SetupResult,
    StatusSnapshot,
    VerifierQuestion,
    VerifierSession,
    VerifierStatus,
)

log = logging.getLogger("istari.localemu")

HEALTH_PATH = "/_localemu/health"
STATUS_REFRESH_SECONDS = 60
# AWS's documentation example key id: the emulator's root. Identity is the key id.
ROOT_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"  # pragma: allowlist secret

T = TypeVar("T")


class LocalEmuClient:
    # Every setup makes a fresh run whose id names its resources; the check grades that run.
    per_attempt_runs = True

    def __init__(
        self,
        base_url: str,
        *,
        region: str = "us-east-1",
        access_key_id: str = ROOT_ACCESS_KEY_ID,
        http: httpx.AsyncClient | None = None,
        timeouts: LocalEmuTimeouts = DEFAULT_TIMEOUTS,
        scenarios: ScenarioRegistry = REGISTRY,
        aws: Aws | None = None,
    ) -> None:
        self.base_url = emulator_endpoint(base_url)
        self.region = region
        self.access_key_id = access_key_id
        self.timeouts = timeouts
        self.scenarios = scenarios
        self._http = http or httpx.AsyncClient(timeout=timeouts.read)
        self._aws = aws or emulator_aws(
            self.base_url, region=region, access_key_id=access_key_id, timeouts=timeouts
        )
        self._snapshot: StatusSnapshot | None = None
        self._refresh_task: asyncio.Task[None] | None = None

    # ── What the browser opens: nothing; the learner's own shell does the work ──
    @property
    def terminal_url(self) -> str | None:
        return None

    @property
    def exam_url(self) -> str | None:
        return None

    @property
    def cli_env(self) -> tuple[str, ...]:
        """What the learner's shell needs so the AWS CLI talks to the emulator as its root."""
        return (
            f"AWS_ENDPOINT_URL={self.base_url}",
            f"AWS_ACCESS_KEY_ID={self.access_key_id}",
            f"AWS_SECRET_ACCESS_KEY={UNCHECKED_SIGNING_KEY}",
            f"AWS_DEFAULT_REGION={self.region}",
        )

    # ── Lifecycle ─────────────────────────────────────────────────────────
    async def aclose(self) -> None:
        if self._refresh_task is not None:
            self._refresh_task.cancel()
        await self._http.aclose()

    def start_background_refresh(self) -> asyncio.Task[None]:
        """Keep the status snapshot fresh so health and the planner never block on the emulator."""

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
        body = await self._health()
        services = body.get("services")
        edition = str(body.get("edition", "") or "")
        version = str(body.get("version", "") or "")
        return VerifierStatus(
            ok=isinstance(services, dict) and bool(services),
            mode=" ".join(part for part in (edition, version) if part) or "localemu",
            profiles=self.scenarios.profiles,
        )

    # ── Questions: Istari's own scenarios ─────────────────────────────────
    async def questions(self, profile: str) -> list[VerifierQuestion]:
        return [s.question() for s in self.scenarios.for_profile(profile)]

    async def question(self, profile: str, question_id: str) -> VerifierQuestion | None:
        scenario = self.scenarios.get(question_id)
        return scenario.question() if scenario is not None and scenario.profile == profile else None

    # ── Runs: the emulator has no sessions, so every setup starts a fresh run ──
    async def ensure_session(self, profile: str) -> VerifierSession:
        return VerifierSession(
            id=secrets.token_hex(3), profile=profile, started_at=datetime.now(UTC)
        )

    # ── Setup, check, teardown ────────────────────────────────────────────
    async def setup(self, question_id: str, *, run: str = "") -> SetupResult:
        """Clear every earlier run of the scenario, then make this run's resources."""
        if not run:
            raise ValueError("a LocalEmu setup needs the attempt's run id")
        scenario, ctx = self._scenario(question_id, run)

        def work() -> str:
            scenario.teardown(self._aws, ctx)
            return scenario.setup(self._aws, ctx)

        output = await self._call(work, doing=f"setting up {question_id}")
        log.info("localemu setup", extra={"event": "localemu.setup", "scenario": question_id})
        return SetupResult(ok=True, output=output)

    async def check(self, question_id: str, *, run: str = "") -> CheckResult:
        if not run:
            # Nothing was set up, so there is nothing to grade: not a failed attempt.
            return CheckResult(
                passed=False, unavailable_reason="Set the lab up first; there is nothing to check."
            )
        scenario, ctx = self._scenario(question_id, run)
        return await self._call(
            lambda: scenario.check(self._aws, ctx), doing=f"checking {question_id}"
        )

    async def solve(self, question_id: str, *, run: str) -> None:
        """Do the task by API, as `make aws-labs-check` does to prove a solved run passes."""
        scenario, ctx = self._scenario(question_id, run)
        await self._call(lambda: scenario.solve(self._aws, ctx), doing=f"solving {question_id}")

    async def teardown(self, question_id: str) -> None:
        """Remove every run of the scenario from the emulator."""
        scenario, ctx = self._scenario(question_id, "")
        await self._call(
            lambda: scenario.teardown(self._aws, ctx), doing=f"tearing down {question_id}"
        )

    # ── Transport ─────────────────────────────────────────────────────────
    def _scenario(self, question_id: str, run: str) -> tuple[Scenario, ScenarioContext]:
        scenario = self.scenarios.get(question_id)
        if scenario is None:
            raise UpstreamError(f"LocalEmu has no scenario '{question_id}' in this Istari build")
        return scenario, ScenarioContext(scenario=scenario.id, run=run, region=self.region)

    async def _call(self, work: Callable[[], T], *, doing: str) -> T:
        try:
            return await anyio.to_thread.run_sync(work)
        except AWS_ERRORS as exc:
            raise upstream_error(self.base_url, exc, doing=doing, timeouts=self.timeouts) from exc

    async def _health(self) -> dict[str, object]:
        url = f"{self.base_url}{HEALTH_PATH}"
        wait = self.timeouts.read
        try:
            response = await self._http.get(url, timeout=wait)
        except httpx.TimeoutException as exc:
            raise UpstreamError(
                f"LocalEmu at {self.base_url} did not answer within {wait:g} s"
            ) from exc
        except httpx.HTTPError as exc:
            raise UpstreamError(f"LocalEmu at {self.base_url} is not reachable: {exc}") from exc
        if response.status_code >= 400:
            raise UpstreamError(
                f"LocalEmu at {self.base_url} answered {response.status_code} for {HEALTH_PATH}",
                details={"status": response.status_code, "path": HEALTH_PATH},
            )
        try:
            body = response.json()
        except ValueError as exc:
            raise UpstreamError(
                f"LocalEmu at {self.base_url} returned a non-JSON health body"
            ) from exc
        if not isinstance(body, dict):
            raise UpstreamError(f"LocalEmu at {self.base_url} returned an unexpected health body")
        return body
