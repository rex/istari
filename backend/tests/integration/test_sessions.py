from __future__ import annotations

import asyncio
import uuid
from typing import Any

from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import Answer
from tests.fixtures import mini_pack

PACK = mini_pack()


def _question(key: str) -> Any:
    questions = PACK["questions"]
    assert isinstance(questions, list)
    return next(q for q in questions if q["slug"] == key)


def _correct(key: str) -> list[str]:
    ids = _question(key)["correct_option_ids"]
    assert isinstance(ids, list)
    return list(ids)


def _wrong(key: str) -> list[str]:
    options = _question(key)["options"]
    assert isinstance(options, list)
    correct = set(_correct(key))
    wrong = [o["id"] for o in options if o["id"] not in correct]
    return wrong[: len(correct)]


async def _start(client: AsyncClient, **body: object) -> Any:
    response = await client.post("/api/sessions", json={"kind": "practice", "minutes": 5, **body})
    assert response.status_code == 201, response.text
    return response.json()


async def _answer(
    client: AsyncClient, session_id: int, position: int, selected: list[str], **extra: object
) -> Any:
    body = {"selected_option_ids": selected, "request_id": uuid.uuid4().hex, **extra}
    response = await client.post(f"/api/sessions/{session_id}/items/{position}/answer", json=body)
    assert response.status_code == 200, response.text
    return response.json()


async def test_five_question_session_grades_by_option_id_after_shuffle(
    study_client: AsyncClient,
) -> None:
    session = await _start(study_client)
    items = session["items"]
    assert len(items) == 5 and session["status"] == "in_progress"
    # Every item: same option ids as the pack, shown in a stored order; no keys leaked.
    shuffled = 0
    for item in items:
        spec = _question(item["item_key"])
        pack_ids = [o["id"] for o in spec["options"]]
        assert sorted(o["id"] for o in item["options"]) == sorted(pack_ids)
        shuffled += [o["id"] for o in item["options"]] != pack_ids
        assert item["feedback"] is None and item["answer"] is None
        assert "correct_option_ids" not in item
    assert shuffled >= 1
    assert (
        "is correct because" not in (await study_client.get(f"/api/sessions/{session['id']}")).text
    )

    correct_total = 0
    for item in items:
        key = item["item_key"]
        selected = _correct(key) if item["position"] % 2 else _wrong(key)
        result = await _answer(
            study_client, session["id"], item["position"], selected, confidence="confident"
        )
        assert result["already_recorded"] is False
        assert result["item"]["answer"]["is_correct"] is (item["position"] % 2 == 1)
        assert result["item"]["feedback"]["correct_option_ids"] == _correct(key)
        assert result["item"]["feedback"]["explanation_md"]
        correct_total += result["item"]["answer"]["is_correct"]

    done = await study_client.post(f"/api/sessions/{session['id']}/complete")
    assert done.status_code == 200
    assert done.json()["status"] == "completed" and done.json()["correct_count"] == correct_total
    assert (await study_client.get("/api/sessions/active")).json() is None


async def test_double_submission_and_retries_record_one_answer(
    study_client: AsyncClient, db: AsyncSession
) -> None:
    session = await _start(study_client)
    key = session["items"][0]["item_key"]
    body = {"selected_option_ids": _correct(key), "request_id": "retry-0001-abcdef"}
    url = f"/api/sessions/{session['id']}/items/1/answer"
    first, second = await asyncio.gather(
        study_client.post(url, json=body), study_client.post(url, json=body)
    )
    assert {first.status_code, second.status_code} == {200}
    assert sorted([first.json()["already_recorded"], second.json()["already_recorded"]]) == [
        False,
        True,
    ]
    third = await study_client.post(url, json={**body, "request_id": "retry-0002-abcdef"})
    assert third.json()["already_recorded"] is True
    count = await db.scalar(select(func.count(Answer.id)))
    assert count == 1


async def test_cardinality_and_unknown_options_are_rejected(study_client: AsyncClient) -> None:
    session = await _start(study_client, focus="objective:2.1")
    multi = next(i for i in session["items"] if i["select_count"] == 2)
    url = f"/api/sessions/{session['id']}/items/{multi['position']}/answer"
    one = await study_client.post(
        url, json={"selected_option_ids": ["o1"], "request_id": uuid.uuid4().hex}
    )
    assert one.status_code == 422 and one.json()["details"]["expected"] == 2
    unknown = await study_client.post(
        url, json={"selected_option_ids": ["o1", "zzz"], "request_id": uuid.uuid4().hex}
    )
    assert unknown.status_code == 422


async def test_draft_is_saved_and_stale_tabs_get_409(study_client: AsyncClient) -> None:
    session = await _start(study_client)
    url = f"/api/sessions/{session['id']}/items/1/draft"
    saved = await study_client.put(
        url, json={"selected_option_ids": ["o2"], "confidence": "uncertain", "expected_version": 1}
    )
    assert saved.status_code == 200 and saved.json()["version"] == 2
    assert saved.json()["items"][0]["draft_selection"] == ["o2"]
    stale = await study_client.put(url, json={"selected_option_ids": ["o3"], "expected_version": 1})
    assert stale.status_code == 409 and stale.json()["details"]["current_version"] == 2
    # Refresh: the newer draft survives.
    fresh = await study_client.get(f"/api/sessions/{session['id']}")
    assert fresh.json()["items"][0]["draft_selection"] == ["o2"]


async def test_assessment_withholds_feedback_until_completion(study_client: AsyncClient) -> None:
    session = await _start(study_client, kind="assessment")
    key = session["items"][0]["item_key"]
    result = await _answer(study_client, session["id"], 1, _correct(key))
    assert result["item"]["answer"]["is_correct"] is None and result["item"]["feedback"] is None
    mid = await study_client.get(f"/api/sessions/{session['id']}")
    assert mid.json()["correct_count"] is None and mid.json()["feedback_visible"] is False
    assert "is correct because" not in mid.text
    done = (await study_client.post(f"/api/sessions/{session['id']}/complete")).json()
    assert done["feedback_visible"] is True and done["correct_count"] == 1
    assert done["items"][0]["feedback"]["correct_option_ids"] == _correct(key)


async def test_second_session_marks_repeats_and_never_duplicates_within(
    study_client: AsyncClient,
) -> None:
    first = await _start(study_client)
    for item in first["items"]:
        await _answer(study_client, first["id"], item["position"], _wrong(item["item_key"]))
    await study_client.post(f"/api/sessions/{first['id']}/complete")
    seen = {i["item_key"] for i in first["items"]}

    second = await _start(study_client)
    keys = [i["item_key"] for i in second["items"]]
    assert len(set(keys)) == len(keys)
    for item in second["items"]:
        result = await _answer(
            study_client, second["id"], item["position"], _correct(item["item_key"])
        )
        assert result["item"]["answer"]["first_attempt"] is (item["item_key"] not in seen)


async def test_only_one_active_session_unless_replaced(study_client: AsyncClient) -> None:
    first = await _start(study_client)
    clash = await study_client.post("/api/sessions", json={"kind": "practice", "minutes": 5})
    assert clash.status_code == 409 and clash.json()["details"]["session_id"] == first["id"]
    replaced = await _start(study_client, replace_active=True)
    assert replaced["id"] != first["id"]
    old = await study_client.get(f"/api/sessions/{first['id']}")
    assert old.json()["status"] == "abandoned"
