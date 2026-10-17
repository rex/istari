"""AWS labs against the LocalEmu stub: health edges, the lab's state, setup and check through
the routes, attempts, and the planner waiting on the emulator rather than the cluster."""

from __future__ import annotations

import copy
import re
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from moto import mock_aws
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.adapters.db.session import session_factory
from app.adapters.localemu import ROOT_ACCESS_KEY_ID, Aws, LocalEmuClient
from app.adapters.localemu.aws import UNCHECKED_SIGNING_KEY
from app.contracts.auth import OnboardingRequest
from app.domain.clock import FixedClock
from app.domain.content.validate import parse_pack
from app.domain.exceptions import UpstreamError
from app.main import create_app
from app.services.content_import import import_pack
from app.services.settings import complete_onboarding
from tests.conftest import OWNER_PASSWORD, OWNER_USERNAME
from tests.fixtures import mini_pack
from tests.localemu_stub import EMULATOR_URL, EmulatorState, HealthMode, moto_aws, stub_localemu

LAB = "lab-aws"


def aws_pack() -> dict[str, object]:
    """The mini pack plus one AWS lab graded by the emulator's S3 versioning scenario."""
    pack = copy.deepcopy(mini_pack())
    labs = pack["labs"]
    assert isinstance(labs, list)
    lab = copy.deepcopy(next(lab for lab in labs if lab["slug"] == "lab-verified"))
    lab.update(
        slug=LAB,
        objectives=["1.2"],
        title="AWS Lab: turn on versioning",
        prerequisites_md="The emulator answers.",
        cost_warning_md="Runs on the emulator; costs nothing.",
        verifier={"backend": "localemu", "profile": "saa", "question": "s3-versioning"},
    )
    labs.append(lab)
    return pack


@pytest.fixture
def emulator() -> EmulatorState:
    return EmulatorState()


@pytest.fixture
def aws() -> Iterator[Aws]:
    with mock_aws():
        yield moto_aws()


@pytest_asyncio.fixture
async def localemu(emulator: EmulatorState, aws: Aws) -> AsyncIterator[LocalEmuClient]:
    client = stub_localemu(emulator, aws)
    yield client
    await client.aclose()


@pytest_asyncio.fixture
async def aws_seeded(engine: AsyncEngine, clock: FixedClock, owner: None) -> None:
    async with session_factory(engine)() as session, session.begin():
        await import_pack(session, parse_pack(aws_pack()), dry_run=False, now=clock.now())
        exam_id = (await session.execute(text("SELECT id FROM exam_versions LIMIT 1"))).scalar_one()
        await complete_onboarding(
            session,
            OnboardingRequest(exam_version_id=exam_id, preferred_session_minutes=5),
            now=clock.now(),
        )


@asynccontextmanager
async def logged_in(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        response = await ac.post(
            "/api/auth/login", json={"username": OWNER_USERNAME, "password": OWNER_PASSWORD}
        )
        assert response.status_code == 200, response.text
        ac.headers["x-csrf-token"] = response.json()["csrf_token"]
        yield ac


# ── The emulator's HTTP edge ──────────────────────────────────────────────
async def test_status_reads_the_health_endpoint(
    localemu: LocalEmuClient, emulator: EmulatorState
) -> None:
    status = await localemu.status()
    assert status.ok and status.mode == "community 1.2.0" and status.session is None
    assert status.profiles == ("saa",) and emulator.health_fetches == 1
    assert localemu.terminal_url is None and localemu.exam_url is None


@pytest.mark.parametrize(
    ("mode", "message"),
    [
        ("down", f"LocalEmu at {EMULATOR_URL} is not reachable: connection refused"),
        ("silent", f"LocalEmu at {EMULATOR_URL} did not answer within 10 s"),
        ("unhealthy", f"LocalEmu at {EMULATOR_URL} answered 503 for /_localemu/health"),
    ],
)
async def test_an_emulator_that_does_not_answer_is_an_upstream_error_and_a_failed_snapshot(
    localemu: LocalEmuClient, emulator: EmulatorState, mode: HealthMode, message: str
) -> None:
    emulator.mode = mode
    with pytest.raises(UpstreamError) as exc:
        await localemu.status()
    assert exc.value.message == message and exc.value.status == 502
    snapshot = await localemu.refresh_snapshot()
    assert snapshot.reachable is False and snapshot.error == message
    assert localemu.snapshot is snapshot


async def test_health_reports_the_emulator_from_the_snapshot_only(
    engine: AsyncEngine, clock: FixedClock, localemu: LocalEmuClient
) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=create_app(engine=engine, clock=clock)),
        base_url="http://testserver",
    ) as ac:
        body = (await ac.get("/api/health")).json()
        assert body["localemu"]["configured"] is False and body["k16s"]["configured"] is False

    app = create_app(engine=engine, clock=clock, localemu=localemu)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        before = (await ac.get("/api/health")).json()["localemu"]
        assert before["configured"] is True and before["reachable"] is None
        await localemu.refresh_snapshot()
        after = (await ac.get("/api/health")).json()["localemu"]
        assert after["reachable"] is True and after["mode"] == "community 1.2.0"
        assert after["profiles"] == ["saa"] and after["checked_at"]


# ── An AWS lab through the routes ─────────────────────────────────────────
async def test_an_aws_lab_without_an_emulator_says_what_to_set(
    aws_seeded: None, engine: AsyncEngine, clock: FixedClock
) -> None:
    async with logged_in(create_app(engine=engine, clock=clock)) as ac:
        state = (await ac.get(f"/api/labs/{LAB}/verifier")).json()
        assert state["configured"] is False and state["reachable"] is False
        assert "LOCALEMU_BASE_URL" in state["message"] and state["spec"]["backend"] == "localemu"
        assert state["attribution"].startswith("Task text from Istari")
        refused = await ac.post(f"/api/labs/{LAB}/setup")
        assert refused.status_code == 409
        assert refused.json()["details"]["code"] == "localemu_unconfigured"


async def test_an_aws_lab_is_set_up_graded_and_regraded_against_the_emulator(
    aws_seeded: None, engine: AsyncEngine, clock: FixedClock, localemu: LocalEmuClient, aws: Aws
) -> None:
    async with logged_in(create_app(engine=engine, clock=clock, localemu=localemu)) as ac:
        state = (await ac.get(f"/api/labs/{LAB}/verifier")).json()
        assert state["configured"] and state["reachable"] and state["mode"] == "community 1.2.0"
        assert state["profile_available"] is True and state["message"] is None
        assert state["task"]["title"] == "Turn on versioning for an S3 bucket"
        assert state["terminal_url"] is None and state["map_url"] is None
        assert state["cli_env"] == [
            f"AWS_ENDPOINT_URL={EMULATOR_URL}",
            f"AWS_ACCESS_KEY_ID={ROOT_ACCESS_KEY_ID}",
            f"AWS_SECRET_ACCESS_KEY={UNCHECKED_SIGNING_KEY}",
            "AWS_DEFAULT_REGION=us-east-1",
        ]

        # Nothing set up yet: ungradable, and no attempt is recorded.
        early = (await ac.post(f"/api/labs/{LAB}/check")).json()
        assert early["attempt"] is None and early["unavailable_reason"].startswith("Set the lab up")

        setup = (await ac.post(f"/api/labs/{LAB}/setup")).json()
        assert setup["ok"] is True and setup["attempt"]["checked_at"] is None
        match = re.search(r"istari-s3-versioning-[0-9a-f]{6}", setup["output"])
        assert match is not None
        bucket = match.group(0)

        failed = (await ac.post(f"/api/labs/{LAB}/check")).json()
        assert failed["passed"] is False and failed["reason_line"] == "FAIL: versioning is off"
        assert failed["attempt"]["id"] == setup["attempt"]["id"]

        # The fix, made the way the learner would, then a re-check grades the same run.
        aws.s3().put_bucket_versioning(Bucket=bucket, VersioningConfiguration={"Status": "Enabled"})
        passed = (await ac.post(f"/api/labs/{LAB}/check")).json()
        assert passed["passed"] is True and passed["reason_line"] == "PASS: versioning is on"
        assert passed["attempt"]["id"] != setup["attempt"]["id"]

        after = (await ac.get(f"/api/labs/{LAB}/verifier")).json()
        assert [a["passed"] for a in after["attempts"]] == [True, False]
        assert after["last_attempt"]["passed"] is True


async def test_the_plan_waits_on_the_emulator_for_an_aws_lab(
    aws_seeded: None, engine: AsyncEngine, clock: FixedClock, localemu: LocalEmuClient
) -> None:
    async with logged_in(create_app(engine=engine, clock=clock, localemu=localemu)) as ac:
        silent = (await ac.get("/api/today?minutes=15")).json()
        assert not [b for b in silent["blocks"] if b["kind"] == "lab"]
        assert (
            "Verified labs are skipped: the AWS emulator is not reachable right now."
            in (silent["explanation"])
        )
        await localemu.refresh_snapshot()
        today = (await ac.get("/api/today?minutes=15")).json()
        [lab] = [b for b in today["blocks"] if b["kind"] == "lab"]
        assert lab["item_key"] == LAB and lab["reason"].startswith("verified on the AWS emulator")
        assert any("the emulator grades it" in line for line in today["explanation"])
