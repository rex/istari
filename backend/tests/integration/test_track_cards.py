"""Track cards: what each pack holds, what has been done on it, and switching tracks."""

from __future__ import annotations

import json
from pathlib import Path

from httpx import AsyncClient

from app.adapters.k16s import K16sClient
from tests.fixtures import mini_pack
from tests.k16s_stub import StubState

CKA_PACK = Path(__file__).resolve().parents[3] / "content" / "packs" / "k8s-cka-k16s" / "pack.json"


def _track(tracks: list[dict[str, object]], code: str) -> dict[str, object]:
    return next(t for t in tracks if t["code"] == code)


def _count(pack: dict[str, object], key: str) -> int:
    items = pack[key]
    assert isinstance(items, list)
    return len(items)


def _verified_labs(pack: dict[str, object]) -> int:
    labs = pack["labs"]
    assert isinstance(labs, list)
    return sum(1 for lab in labs if isinstance(lab, dict) and lab.get("verifier"))


async def test_tracks_carry_counts_then_progress_once_something_was_done(
    verified_client: AsyncClient, stub_k16s: K16sClient, stub: StubState
) -> None:
    pack = mini_pack()
    before = _track((await verified_client.get("/api/tracks")).json(), "TST-C01")
    assert before["counts"] == {
        "lessons": _count(pack, "lessons"),
        "questions": _count(pack, "questions"),
        "cards": _count(pack, "flashcards"),
        "labs": _count(pack, "labs"),
    }
    assert before["progress"] is None and before["last_studied_at"] is None

    await stub_k16s.refresh_snapshot()
    stub.results["stub-01-crashloop"] = True
    await verified_client.post("/api/labs/lab-verified/setup")
    assert (await verified_client.post("/api/labs/lab-verified/check")).json()["passed"] is True

    after = _track((await verified_client.get("/api/tracks")).json(), "TST-C01")
    progress = after["progress"]
    assert isinstance(progress, dict)
    # Coverage in words: the lessons clause stays at zero, the labs clause counts the pass.
    assert progress["sentence"] == (
        f"0 of {_count(pack, 'lessons')} lessons read {chr(0xB7)} "
        f"1 of {_verified_labs(pack)} labs verified"
    )
    assert 0 < float(str(progress["fraction"])) < 1
    assert after["last_studied_at"] is not None
    # /api/me carries the same cards for the picker.
    me = (await verified_client.get("/api/me")).json()
    assert _track(me["available_tracks"], "TST-C01")["progress"] == progress
    assert me["track"]["counts"] is None


async def test_the_active_track_switches_through_settings(study_client: AsyncClient) -> None:
    imported = await study_client.post(
        "/api/content/import",
        json={"pack": json.loads(CKA_PACK.read_text(encoding="utf-8")), "dry_run": False},
    )
    assert imported.status_code == 200, imported.text
    cka = _track((await study_client.get("/api/tracks")).json(), "CKA-1.35")
    assert cka["counts"] == {"lessons": 0, "questions": 0, "cards": 0, "labs": 36}

    switched = await study_client.patch(
        "/api/settings", json={"active_exam_version_id": cka["exam_version_id"]}
    )
    assert switched.status_code == 200, switched.text
    assert switched.json()["active_exam_version_id"] == cka["exam_version_id"]
    me = (await study_client.get("/api/me")).json()
    assert me["track"]["code"] == "CKA-1.35" and me["onboarding_required"] is False

    missing = await study_client.patch("/api/settings", json={"active_exam_version_id": 999999})
    assert missing.status_code == 404
