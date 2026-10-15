"""The K16S adapter against the stub server: status, questions, sessions, setup, check, errors."""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine

from app.adapters.k16s import K16sClient, K16sTimeouts
from app.adapters.k16s.client import DEFAULT_TIMEOUTS
from app.domain.clock import FixedClock
from app.domain.exceptions import UpstreamError
from app.main import create_app
from tests.k16s_stub import StubState, create_stub

STUB_URL = "http://k16s.test"


@pytest.fixture
def stub_app() -> FastAPI:
    return create_stub()


@pytest.fixture
def stub(stub_app: FastAPI) -> StubState:
    state: StubState = stub_app.state.stub
    return state


def stub_client(stub_app: FastAPI, timeouts: K16sTimeouts = DEFAULT_TIMEOUTS) -> K16sClient:
    http = httpx.AsyncClient(transport=httpx.ASGITransport(app=stub_app), base_url=STUB_URL)
    return K16sClient(STUB_URL, public_url="http://k16s.lan:8080", http=http, timeouts=timeouts)


@pytest_asyncio.fixture
async def k16s(stub_app: FastAPI) -> AsyncIterator[K16sClient]:
    client = stub_client(stub_app)
    yield client
    await client.aclose()


async def test_status_lists_profiles_and_no_session(k16s: K16sClient) -> None:
    status = await k16s.status()
    assert status.ok and status.mode == "full" and status.session is None
    assert status.profiles == ("cka", "cka2")
    assert k16s.terminal_url == "http://k16s.lan:8080/terminal/"


async def test_questions_are_cached_for_a_minute(k16s: K16sClient, stub: StubState) -> None:
    first = await k16s.questions("cka")
    again = await k16s.questions("cka")
    assert [q.id for q in first] == ["stub-01-crashloop", "stub-03-passing"] and again == first
    assert stub.question_fetches == 1
    heavy = await k16s.question("cka2", "stub-02-heavy")
    assert heavy is not None and heavy.requires == "heavy" and heavy.weight == 6
    assert await k16s.question("cka", "nope") is None


async def test_sessions_are_reused_on_the_same_profile_and_switched_when_needed(
    k16s: K16sClient, stub: StubState
) -> None:
    first = await k16s.ensure_session("cka")
    same = await k16s.ensure_session("cka")
    assert first.id == same.id and first.profile == "cka" and stub.session_starts == 1
    switched = await k16s.ensure_session("cka2")
    assert switched.profile == "cka2" and switched.id != first.id and stub.session_starts == 2
    assert stub.session is not None and stub.session["profile"] == "cka2"


async def test_setup_and_check_map_the_grader_output(k16s: K16sClient, stub: StubState) -> None:
    await k16s.ensure_session("cka")
    setup = await k16s.setup("stub-01-crashloop")
    assert setup.ok and "environment ready" in setup.output and setup.unavailable_reason is None
    failed = await k16s.check("stub-01-crashloop")
    assert failed.passed is False
    assert failed.reason_line == "FAIL: pod web-0 is still CrashLoopBackOff"
    stub.results["stub-01-crashloop"] = True
    passed = await k16s.check("stub-01-crashloop")
    assert passed.passed is True and passed.reason_line == "PASS: the task is complete"
    assert stub.setups == ["stub-01-crashloop"] and len(stub.checks) == 2


async def test_unavailable_tasks_report_the_reason_not_an_error(
    k16s: K16sClient, stub: StubState
) -> None:
    stub.mode = "lightweight"
    await k16s.ensure_session("cka2")
    setup = await k16s.setup("stub-02-heavy")
    assert setup.ok is False and setup.unavailable_reason and "full VM" in setup.unavailable_reason
    check = await k16s.check("stub-02-heavy")
    assert check.passed is False and check.unavailable_reason == setup.unavailable_reason


async def test_a_slow_backend_is_an_upstream_error_with_the_timeout_named() -> None:
    # The in-process ASGI transport never times out, so the timeout is raised by a transport
    # that behaves like a silent server; the client must turn it into the owner's sentence.
    def silent(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("no answer", request=request)

    http = httpx.AsyncClient(transport=httpx.MockTransport(silent), base_url=STUB_URL)
    client = K16sClient(STUB_URL, http=http, timeouts=K16sTimeouts(check=45.0))
    try:
        with pytest.raises(UpstreamError) as exc:
            await client.check("stub-01-crashloop")
        assert exc.value.message == f"K16S at {STUB_URL} did not answer within 45 s"
        assert exc.value.status == 502
    finally:
        await client.aclose()


async def test_backend_errors_carry_status_and_message(k16s: K16sClient) -> None:
    with pytest.raises(UpstreamError) as exc:
        await k16s.check("stub-01-crashloop")  # no session yet
    assert "400" in exc.value.message and "no active session" in exc.value.message
    assert exc.value.details == {"status": 400, "path": "/api/questions/stub-01-crashloop/check"}


async def test_an_unreachable_host_is_an_upstream_error_and_a_failed_snapshot() -> None:
    client = K16sClient("http://127.0.0.1:9", timeouts=K16sTimeouts(read=1.0))
    try:
        with pytest.raises(UpstreamError) as exc:
            await client.status()
        assert "not reachable" in exc.value.message
        snapshot = await client.refresh_snapshot()
        assert snapshot.reachable is False and snapshot.error and client.snapshot is snapshot
    finally:
        await client.aclose()


async def test_health_reports_the_backend_from_the_snapshot_only(
    engine: AsyncEngine, clock: FixedClock, stub_app: FastAPI
) -> None:
    unconfigured = create_app(engine=engine, clock=clock)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=unconfigured), base_url="http://testserver"
    ) as ac:
        body = (await ac.get("/api/health")).json()
        assert body["k16s"] == {
            "configured": False,
            "reachable": None,
            "mode": None,
            "profiles": [],
            "checked_at": None,
        }

    k16s = stub_client(stub_app)
    configured = create_app(engine=engine, clock=clock, k16s=k16s)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=configured), base_url="http://testserver"
        ) as ac:
            before = (await ac.get("/api/health")).json()["k16s"]
            assert before["configured"] is True and before["reachable"] is None
            await k16s.refresh_snapshot()
            after = (await ac.get("/api/health")).json()["k16s"]
            assert after["reachable"] is True and after["profiles"] == ["cka", "cka2"]
            assert after["mode"] == "full" and after["checked_at"]
    finally:
        await k16s.aclose()
