from __future__ import annotations

import uuid

from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import Answer, ContentItem, ContentRevision, Note
from tests.fixtures import mini_pack, pack_with_changed_question


async def test_dry_run_changes_nothing(auth_client: AsyncClient, db: AsyncSession) -> None:
    response = await auth_client.post(
        "/api/content/import", json={"pack": mini_pack(), "dry_run": True}
    )
    assert response.status_code == 200, response.text
    report = response.json()
    assert report["dry_run"] is True and report["counts"]["created"] == 14
    assert await db.scalar(select(func.count(ContentItem.id))) == 0


async def test_reimport_is_idempotent_and_edits_create_revisions(
    study_client: AsyncClient, db: AsyncSession
) -> None:
    again = await study_client.post(
        "/api/content/import", json={"pack": mini_pack(), "dry_run": False}
    )
    assert again.json()["counts"] == {"created": 0, "updated": 0, "unchanged": 14, "retired": 0}

    # Learning history on q-1 before the edit, plus a personal note.
    session = (
        await study_client.post(
            "/api/sessions", json={"kind": "practice", "minutes": 5, "focus": "objective:1.1"}
        )
    ).json()
    q1 = next(i for i in session["items"] if i["item_key"] == "q-1")
    await study_client.post(
        f"/api/sessions/{session['id']}/items/{q1['position']}/answer",
        json={"selected_option_ids": ["o1"], "request_id": uuid.uuid4().hex},
    )
    note = await study_client.post(
        "/api/notes", json={"item_key": "q-1", "body_md": "remember this"}
    )
    assert note.status_code == 201

    changed = await study_client.post(
        "/api/content/import", json={"pack": pack_with_changed_question(), "dry_run": False}
    )
    report = changed.json()
    assert report["updated"] == ["q-1"] and report["retired"] == ["q-8"]

    item = await db.scalar(select(ContentItem).where(ContentItem.item_key == "q-1"))
    assert item is not None
    revisions = (
        await db.scalars(
            select(ContentRevision)
            .where(ContentRevision.item_id == item.id)
            .order_by(ContentRevision.revision)
        )
    ).all()
    assert [r.revision for r in revisions] == [1, 2] and [r.is_current for r in revisions] == [
        False,
        True,
    ]
    answer = await db.scalar(select(Answer).where(Answer.item_id == item.id))
    assert (
        answer is not None and answer.revision_id == revisions[0].id
    )  # history points at what was shown
    assert await db.scalar(select(func.count(Note.id))) == 1
    retired = await db.scalar(select(ContentItem).where(ContentItem.item_key == "q-8"))
    assert retired is not None and retired.status == "retired"

    # The retired question no longer enters sessions; the edited one shows the new wording.
    detail = await study_client.get("/api/content/items/q-1")
    assert "reworded" in detail.json()["content"]["stem_md"] and detail.json()["revisions"] == [
        1,
        2,
    ]


async def test_export_round_trips_through_the_schema(study_client: AsyncClient) -> None:
    exported = await study_client.get("/api/content/export/mini-test-pack")
    assert exported.status_code == 200
    data = exported.json()
    assert data["pack"]["slug"] == "mini-test-pack" and len(data["questions"]) == 8
    reimport = await study_client.post("/api/content/import", json={"pack": data, "dry_run": True})
    assert reimport.json()["counts"]["unchanged"] == 14


async def test_invalid_pack_is_rejected_with_details(auth_client: AsyncClient) -> None:
    broken = mini_pack()
    questions = broken["questions"]
    assert isinstance(questions, list)
    questions[0]["objectives"] = ["7.7"]
    response = await auth_client.post(
        "/api/content/import", json={"pack": broken, "dry_run": False}
    )
    assert response.status_code == 422
    assert response.json()["details"]["errors"][0]["code"] == "unknown_objective"


async def test_editing_through_the_api_validates_and_versions(study_client: AsyncClient) -> None:
    detail = (await study_client.get("/api/content/items/q-2")).json()
    body = {
        **detail["content"],
        "objectives": detail["objectives"],
        "sources": detail["sources"],
        "provenance": detail["provenance"],
        "review_status": detail["review_status"],
    }
    body["distractor_rationales"] = {}
    bad = await study_client.put("/api/content/items/q-2", json={"item": body})
    assert bad.status_code == 422
    body["distractor_rationales"] = detail["content"]["distractor_rationales"]
    body["stem_md"] = "Edited stem for q-2"
    good = await study_client.put("/api/content/items/q-2", json={"item": body})
    assert good.status_code == 200 and good.json()["revision"] == 2
    flagged = await study_client.patch(
        "/api/content/items/q-2/flags", json={"status": "invalidated"}
    )
    assert flagged.json()["status"] == "invalidated"
