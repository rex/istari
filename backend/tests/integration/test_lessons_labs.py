from __future__ import annotations

from httpx import AsyncClient


async def test_lesson_reading_progress_bookmarks_and_notes(study_client: AsyncClient) -> None:
    lessons = (await study_client.get("/api/lessons")).json()
    assert [entry["item_key"] for entry in lessons] == ["lesson-one", "lesson-two"]
    lesson = (await study_client.get("/api/lessons/lesson-one")).json()
    assert (
        lesson["body_md"].startswith("## Heading")
        and lesson["checks"][0]["answer_md"] == "Because."
    )
    assert lesson["authored_by"] == "ai" and lesson["review_status"] == "source_checked"
    assert lesson["progress"]["last_opened_at"] is not None

    saved = await study_client.patch(
        "/api/lessons/lesson-one/progress",
        json={"position": 0.42, "bookmarked": True, "completed": True},
    )
    assert saved.json()["position"] == 0.42 and saved.json()["bookmarked"] is True
    assert saved.json()["completed_at"] is not None

    note = await study_client.post(
        "/api/notes", json={"item_key": "lesson-one", "body_md": "key insight"}
    )
    assert note.status_code == 201
    again = (await study_client.get("/api/lessons/lesson-one")).json()
    assert again["notes"][0]["body_md"] == "key insight" and again["progress"]["completed_at"]
    edited = await study_client.patch(
        f"/api/notes/{note.json()['id']}", json={"body_md": "sharper insight"}
    )
    assert edited.json()["body_md"] == "sharper insight"
    listed = (await study_client.get("/api/notes?item_key=lesson-one")).json()
    assert len(listed) == 1
    assert (await study_client.delete(f"/api/notes/{note.json()['id']}")).status_code == 200
    assert (await study_client.get("/api/notes?item_key=lesson-one")).json() == []


async def test_lab_brief_and_evidence_lifecycle(study_client: AsyncClient) -> None:
    labs = (await study_client.get("/api/labs")).json()
    assert labs[0]["item_key"] == "lab-one" and labs[0]["evidence_count"] == 0
    lab = (await study_client.get("/api/labs/lab-one")).json()
    assert "charges" in lab["cost_warning_md"] and lab["cleanup_md"]
    added = await study_client.post(
        "/api/labs/lab-one/evidence", json={"body_md": "Saw the bucket listed."}
    )
    assert added.status_code == 201
    updated = await study_client.patch(
        f"/api/labs/evidence/{added.json()['id']}",
        json={"body_md": "Saw the bucket listed, then deleted it."},
    )
    assert "deleted" in updated.json()["body_md"]
    assert (await study_client.get("/api/labs/lab-one")).json()["evidence_count"] == 1
    assert (
        await study_client.delete(f"/api/labs/evidence/{added.json()['id']}")
    ).status_code == 200
    assert (await study_client.get("/api/labs/lab-one")).json()["evidence"] == []


async def test_track_and_errors_have_stable_shapes(study_client: AsyncClient) -> None:
    track = (await study_client.get("/api/track")).json()
    assert track["code"] == "TST-C01" and [d["code"] for d in track["domains"]] == ["1", "2"]
    assert track["verification_status"] == "unverified"
    missing = await study_client.get("/api/lessons/does-not-exist")
    assert missing.status_code == 404 and missing.json()["error"] == "not_found"
    invalid = await study_client.post("/api/sessions", json={"kind": "exam", "minutes": 7})
    assert invalid.status_code == 422 and invalid.json()["error"] == "invalid_request"
