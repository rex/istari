from __future__ import annotations

import uuid
from typing import Any

from httpx import AsyncClient

from tests.fixtures import mini_pack

PACK = mini_pack()


def _spec(key: str) -> Any:
    questions = PACK["questions"]
    assert isinstance(questions, list)
    return next(q for q in questions if q["slug"] == key)


def _correct(key: str) -> list[str]:
    return list(_spec(key)["correct_option_ids"])


def _wrong(key: str) -> list[str]:
    spec = _spec(key)
    correct = set(spec["correct_option_ids"])
    return [o["id"] for o in spec["options"] if o["id"] not in correct][: len(correct)]


async def _practice(
    client: AsyncClient, focus: str, *, wrong: bool, confidence: str = "confident"
) -> None:
    session = (
        await client.post("/api/sessions", json={"kind": "practice", "minutes": 5, "focus": focus})
    ).json()
    for item in session["items"]:
        selected = _wrong(item["item_key"]) if wrong else _correct(item["item_key"])
        await client.post(
            f"/api/sessions/{session['id']}/items/{item['position']}/answer",
            json={
                "selected_option_ids": selected,
                "request_id": uuid.uuid4().hex,
                "confidence": confidence,
            },
        )
    await client.post(f"/api/sessions/{session['id']}/complete")


async def test_today_without_evidence_recommends_reviews_then_mixed_practice(
    study_client: AsyncClient,
) -> None:
    today = (await study_client.get("/api/today?minutes=5")).json()
    kinds = [b["kind"] for b in today["blocks"]]
    assert kinds == ["review", "practice"]
    assert today["blocks"][1]["focus"] == "mixed" and today["blocks"][1]["count"] == 5
    assert today["active_session"] is None and today["exam"]["code"] == "TST-C01"
    assert any("mixed" in line for line in today["explanation"])


async def test_today_prefers_resume_then_weakest_objective(study_client: AsyncClient) -> None:
    session = (
        await study_client.post("/api/sessions", json={"kind": "practice", "minutes": 5})
    ).json()
    today = (await study_client.get("/api/today")).json()
    assert (
        today["blocks"][0]["kind"] == "resume" and today["blocks"][0]["session_id"] == session["id"]
    )
    await study_client.post(f"/api/sessions/{session['id']}/abandon")

    await _practice(study_client, "objective:1.1", wrong=True)
    today = (await study_client.get("/api/today?minutes=15")).json()
    practice = next(b for b in today["blocks"] if b["kind"] == "practice")
    assert practice.get("focus", "").startswith("objective:1.1")
    assert today["weakest"][0]["code"] == "1.1"
    assert today["recent"]["answers_7d"] == 5


async def test_progress_separates_first_attempt_from_repeats_and_labels_evidence(
    study_client: AsyncClient,
) -> None:
    before = (await study_client.get("/api/progress")).json()
    assert before["totals"]["first_attempts"] == 0
    assert all(o["evidence"] == "insufficient" for d in before["domains"] for o in d["objectives"])
    assert (
        "readiness" not in before["evidence_note"].lower()
        or "not evidence" in before["evidence_note"]
    )

    await _practice(study_client, "objective:1.1", wrong=True)  # 3 first attempts wrong on 1.1
    await _practice(
        study_client, "objective:1.1", wrong=False, confidence="guessing"
    )  # repeats, correct

    progress = (await study_client.get("/api/progress")).json()
    obj = next(o for d in progress["domains"] for o in d["objectives"] if o["code"] == "1.1")
    assert obj["first_attempts"] == 3 and obj["first_correct"] == 0 and obj["evidence"] == "weak"
    assert obj["repeat_attempts"] == 3 and obj["repeat_correct"] == 3
    assert progress["weak_areas"][0]["code"] == "1.1"
    assert len(progress["confident_mistakes"]) >= 1
    assert progress["next_action"] is not None
    assert (
        len(progress["recent_activity"]) == 14 and progress["recent_activity"][-1]["answers"] == 10
    )

    # Invalidating a question flags analytics and drops its answers from the figures.
    key = progress["confident_mistakes"][0]["item_key"]
    await study_client.patch(f"/api/content/items/{key}/flags", json={"status": "invalidated"})
    flagged = (await study_client.get("/api/progress")).json()
    assert flagged["flags"]["invalidated_items"] == 1 and flagged["flags"]["excluded_answers"] >= 1
    assert flagged["totals"]["first_attempts"] < progress["totals"]["first_attempts"]


async def test_onboarding_is_one_call_and_familiar_is_not_mastery(
    auth_client: AsyncClient, seeded: int
) -> None:
    me = (await auth_client.get("/api/me")).json()
    assert me["onboarding_required"] is False and me["track"]["code"] == "TST-C01"
    done = await auth_client.post(
        "/api/onboarding",
        json={
            "exam_version_id": seeded,
            "exam_date": "2026-12-01",
            "preferred_session_minutes": 15,
            "familiar_objective_codes": ["2.1"],
        },
    )
    assert done.status_code == 200 and done.json()["familiar_objective_codes"] == ["2.1"]
    progress = (await auth_client.get("/api/progress")).json()
    obj = next(o for d in progress["domains"] for o in d["objectives"] if o["code"] == "2.1")
    assert obj["self_declared_familiar"] is True and obj["evidence"] == "insufficient"
    lessons = (await auth_client.get("/api/lessons")).json()
    assert (
        next(x for x in lessons if x["item_key"] == "lesson-two")["self_declared_familiar"] is True
    )
    today = (await auth_client.get("/api/today?minutes=30")).json()
    lesson_block = next(b for b in today["blocks"] if b["kind"] == "lesson")
    assert lesson_block["item_key"] == "lesson-one"
    assert today["exam"]["days_left"] == 57
