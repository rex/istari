"""Verified labs in the plan and on Progress: scheduled only while the cluster answers,
first graded attempt is the evidence, later attempts are repeats."""

from __future__ import annotations

from httpx import AsyncClient

from app.adapters.k16s import K16sClient
from tests.k16s_stub import StubState


def _blocks(today: dict[str, object]) -> list[dict[str, object]]:
    blocks = today["blocks"]
    assert isinstance(blocks, list)
    return blocks


async def test_today_schedules_one_verified_lab_when_the_cluster_answers(
    verified_client: AsyncClient, stub_k16s: K16sClient
) -> None:
    await stub_k16s.refresh_snapshot()
    today = (await verified_client.get("/api/today?minutes=15")).json()
    labs = [b for b in _blocks(today) if b["kind"] == "lab"]
    assert len(labs) == 1 and labs[0]["item_key"] == "lab-verified"
    assert labs[0]["count"] == 1 and "serves objective 2.1" in str(labs[0]["reason"])
    assert any("serves objective 2.1 (Objective 2.1)" in line for line in today["explanation"])
    # Five minutes is too short for a lab; nothing is said about it either.
    short = (await verified_client.get("/api/today?minutes=5")).json()
    assert not [b for b in _blocks(short) if b["kind"] == "lab"]
    assert not any("lab" in line.lower() for line in short["explanation"])


async def test_today_skips_verified_labs_and_says_so_when_the_cluster_is_silent(
    verified_client: AsyncClient,
) -> None:
    # No snapshot yet: the client is configured but has never heard from the cluster.
    today = (await verified_client.get("/api/today?minutes=30")).json()
    assert not [b for b in _blocks(today) if b["kind"] == "lab"]
    assert any("not reachable" in line for line in today["explanation"])


async def test_today_without_a_backend_never_mentions_labs(study_client: AsyncClient) -> None:
    today = (await study_client.get("/api/today?minutes=30")).json()
    assert not [b for b in _blocks(today) if b["kind"] == "lab"]
    assert not any("lab" in line.lower() for line in today["explanation"])


async def test_first_graded_attempt_is_the_evidence(
    verified_client: AsyncClient, stub_k16s: K16sClient, stub: StubState
) -> None:
    await stub_k16s.refresh_snapshot()
    before = (await verified_client.get("/api/progress")).json()
    assert before["totals"]["labs_total"] == 2 and before["totals"]["labs_attempted"] == 0

    # lab-verified: first attempt passes.
    stub.results["stub-01-crashloop"] = True
    await verified_client.post("/api/labs/lab-verified/setup")
    assert (await verified_client.post("/api/labs/lab-verified/check")).json()["passed"] is True
    # lab-verified-two: first attempt fails, the second passes; only the first counts.
    await verified_client.post("/api/labs/lab-verified-two/setup")
    assert (await verified_client.post("/api/labs/lab-verified-two/check")).json()[
        "passed"
    ] is False
    stub.results["stub-02-heavy"] = True
    assert (await verified_client.post("/api/labs/lab-verified-two/check")).json()["passed"] is True

    progress = (await verified_client.get("/api/progress")).json()
    totals = progress["totals"]
    assert (totals["labs_total"], totals["labs_attempted"], totals["labs_passed_first"]) == (
        2,
        2,
        1,
    )
    objectives = {o["code"]: o for d in progress["domains"] for o in d["objectives"]}
    assert (objectives["2.1"]["labs_total"], objectives["2.1"]["labs_passed_first"]) == (1, 1)
    assert (objectives["1.1"]["labs_total"], objectives["1.1"]["labs_passed_first"]) == (1, 0)
    assert objectives["1.1"]["labs_attempted"] == 1
    domains = {d["code"]: d for d in progress["domains"]}
    assert domains["2"]["labs_passed_first"] == 1 and domains["1"]["labs_passed_first"] == 0
    assert "first graded attempt" in progress["evidence_note"]

    # Both labs have passed at some point, so the planner has nothing left to schedule.
    today = (await verified_client.get("/api/today?minutes=30")).json()
    assert not [b for b in _blocks(today) if b["kind"] == "lab"]


async def test_the_planner_moves_on_to_the_next_open_lab(
    verified_client: AsyncClient, stub_k16s: K16sClient, stub: StubState
) -> None:
    await stub_k16s.refresh_snapshot()
    stub.results["stub-01-crashloop"] = True
    await verified_client.post("/api/labs/lab-verified/setup")
    await verified_client.post("/api/labs/lab-verified/check")
    today = (await verified_client.get("/api/today?minutes=30")).json()
    labs = [b for b in _blocks(today) if b["kind"] == "lab"]
    assert [b["item_key"] for b in labs] == ["lab-verified-two"]
    assert today["blocks"][-1]["kind"] in {"lab", "lesson"}
