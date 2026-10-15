"""Verified labs end to end against the stub: state, setup, check, attempts, failures."""

from __future__ import annotations

from datetime import timedelta

import httpx
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.adapters.db.models import LabAttempt
from app.adapters.k16s import K16sClient
from app.domain.clock import FixedClock
from app.main import create_app
from tests.conftest import FROZEN_NOW, OWNER_PASSWORD, OWNER_USERNAME, STUB_URL
from tests.k16s_stub import StubState


async def test_a_manual_lab_has_no_verifier(verified_client: AsyncClient) -> None:
    response = await verified_client.get("/api/labs/lab-one/verifier")
    assert response.status_code == 404 and "done by hand" in response.json()["message"]
    labs = {lab["item_key"]: lab for lab in (await verified_client.get("/api/labs")).json()}
    assert labs["lab-one"]["verifier"] is None and labs["lab-one"]["attempt_count"] == 0
    assert labs["lab-verified"]["verifier"]["question"] == "stub-01-crashloop"


async def test_without_a_backend_the_state_explains_and_setup_refuses(
    study_client: AsyncClient,
) -> None:
    state = (await study_client.get("/api/labs/lab-verified/verifier")).json()
    assert state["configured"] is False and state["reachable"] is False
    assert "K16S_BASE_URL" in state["message"] and state["terminal_url"] is None
    assert state["spec"]["profile"] == "cka" and state["attempts"] == []
    refused = await study_client.post("/api/labs/lab-verified/setup")
    assert refused.status_code == 409 and refused.json()["details"]["code"] == "k16s_unconfigured"


async def test_state_shows_the_live_task_and_the_links(verified_client: AsyncClient) -> None:
    state = (await verified_client.get("/api/labs/lab-verified/verifier")).json()
    assert state["configured"] and state["reachable"] and state["mode"] == "full"
    assert state["profile_available"] is True and state["session_profile"] is None
    assert state["task"]["title"] == "Stub: a pod keeps crashing" and state["task"]["weight"] == 4
    assert state["terminal_url"] == "http://k16s.lan:8080/terminal/"
    assert state["exam_url"] == "http://k16s.lan:8080/" and state["map_url"] is None
    assert state["unavailable_reason"] is None and state["message"] is None
    assert "K16S" in state["attribution"] and state["last_attempt"] is None


async def test_setup_then_check_records_one_attempt_and_a_pass_records_another(
    verified_client: AsyncClient, stub: StubState, clock: FixedClock
) -> None:
    setup = (await verified_client.post("/api/labs/lab-verified/setup")).json()
    assert setup["ok"] is True and "environment ready" in setup["output"]
    attempt = setup["attempt"]
    assert attempt["setup_at"] and attempt["checked_at"] is None and attempt["passed"] is None
    assert stub.session is not None and stub.session["profile"] == "cka"

    clock.set(FROZEN_NOW + timedelta(seconds=90))
    failed = (await verified_client.post("/api/labs/lab-verified/check")).json()
    assert failed["passed"] is False
    assert failed["reason_line"] == "FAIL: pod web-0 is still CrashLoopBackOff"
    assert failed["attempt"]["id"] == attempt["id"] and failed["attempt"]["duration_seconds"] == 90

    labs = {lab["item_key"]: lab for lab in (await verified_client.get("/api/labs")).json()}
    card = labs["lab-verified"]
    assert card["attempt_count"] == 1 and card["last_attempt"]["passed"] is False
    assert card["last_attempt"]["reason_line"].startswith("FAIL:")

    stub.results["stub-01-crashloop"] = True
    passed = (await verified_client.post("/api/labs/lab-verified/check")).json()
    assert passed["passed"] is True and passed["attempt"]["id"] != attempt["id"]
    assert passed["attempt"]["setup_at"] is None and passed["attempt"]["duration_seconds"] is None

    state = (await verified_client.get("/api/labs/lab-verified/verifier")).json()
    assert [a["passed"] for a in state["attempts"]] == [True, False]
    assert state["last_attempt"]["passed"] is True and state["session_profile"] == "cka"
    assert stub.session_starts == 1  # one session carried every call on this profile


async def test_profile_switch_and_unavailable_tasks(
    verified_client: AsyncClient, stub: StubState
) -> None:
    stub.mode = "lightweight"
    first = await verified_client.post("/api/labs/lab-verified/setup")
    assert first.status_code == 200 and stub.session_starts == 1
    state = (await verified_client.get("/api/labs/lab-verified-two/verifier")).json()
    assert state["session_profile"] == "cka" and state["unavailable_reason"]
    heavy = (await verified_client.post("/api/labs/lab-verified-two/setup")).json()
    assert stub.session_starts == 2 and stub.session is not None
    assert stub.session["profile"] == "cka2"
    assert heavy["ok"] is False and heavy["attempt"] is None
    assert "full VM" in heavy["unavailable_reason"]
    check = (await verified_client.post("/api/labs/lab-verified-two/check")).json()
    assert check["passed"] is False and check["attempt"] is None and check["unavailable_reason"]
    after = (await verified_client.get("/api/labs/lab-verified-two/verifier")).json()
    assert after["attempts"] == []  # nothing ran, nothing recorded


async def test_a_transport_failure_is_a_502_and_records_nothing(
    engine: AsyncEngine, clock: FixedClock, owner: None, seeded: int, db: AsyncSession
) -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    k16s = K16sClient(
        STUB_URL, http=httpx.AsyncClient(transport=httpx.MockTransport(refuse), base_url=STUB_URL)
    )
    app = create_app(engine=engine, clock=clock, k16s=k16s)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as ac:
            login = await ac.post(
                "/api/auth/login", json={"username": OWNER_USERNAME, "password": OWNER_PASSWORD}
            )
            ac.headers["x-csrf-token"] = login.json()["csrf_token"]
            failed = await ac.post("/api/labs/lab-verified/setup")
            assert failed.status_code == 502 and failed.json()["error"] == "upstream_error"
            assert "not reachable" in failed.json()["message"]
            state = (await ac.get("/api/labs/lab-verified/verifier")).json()
            assert state["configured"] is True and state["reachable"] is False
            assert "not reachable" in state["message"] and state["terminal_url"]
    finally:
        await k16s.aclose()
    assert await db.scalar(select(func.count(LabAttempt.id))) == 0
