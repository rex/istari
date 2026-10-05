from __future__ import annotations

import uuid
from datetime import UTC, datetime

from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import ReviewEvent
from app.domain.clock import FixedClock


async def test_pack_flashcards_are_due_as_new_cards(study_client: AsyncClient) -> None:
    due = (await study_client.get("/api/reviews/due")).json()
    assert due["due_total"] == 3 and due["new_total"] == 3 and len(due["cards"]) == 3
    assert due["cards"][0]["due_local"].endswith("-05:00")  # America/Chicago default
    assert due["cards"][0]["source_item_key"].startswith("fc-")


async def test_rating_persists_and_is_idempotent(
    study_client: AsyncClient, db: AsyncSession
) -> None:
    card = (await study_client.get("/api/reviews/due")).json()["cards"][0]
    body = {"rating": 3, "request_id": "rate-0001-abcdef", "duration_ms": 4200}
    first = await study_client.post(f"/api/reviews/cards/{card['id']}/rate", json=body)
    assert first.status_code == 200 and first.json()["already_recorded"] is False
    assert first.json()["card"]["due"] > card["due"]
    assert first.json()["reviewed_today"] == 1
    second = await study_client.post(f"/api/reviews/cards/{card['id']}/rate", json=body)
    assert second.json()["already_recorded"] is True
    assert await db.scalar(select(func.count(ReviewEvent.id))) == 1
    event = await db.scalar(select(ReviewEvent))
    assert event is not None and event.scheduler_version.startswith("py-fsrs ")
    assert event.state_before == 1 and event.due_after > event.due_before


async def test_daily_limit_and_recovery_mode_bound_the_queue(study_client: AsyncClient) -> None:
    await study_client.patch("/api/settings", json={"daily_review_limit": 1})
    due = (await study_client.get("/api/reviews/due")).json()
    assert len(due["cards"]) == 1 and due["remaining_today"] == 1
    await study_client.post(
        f"/api/reviews/cards/{due['cards'][0]['id']}/rate",
        json={"rating": 4, "request_id": uuid.uuid4().hex},
    )
    after = (await study_client.get("/api/reviews/due")).json()
    assert after["cards"] == [] and after["remaining_today"] == 0 and after["due_total"] == 2
    await study_client.patch(
        "/api/settings", json={"daily_review_limit": 100, "backlog_mode": "recovery"}
    )
    recovery = (await study_client.get("/api/reviews/due")).json()
    assert recovery["backlog_mode"] == "recovery" and len(recovery["cards"]) == 2


async def test_reviewed_today_follows_the_local_midnight(
    study_client: AsyncClient, clock: FixedClock
) -> None:
    clock.set(datetime(2026, 10, 6, 3, 0, tzinfo=UTC))  # 22:00 CDT on Oct 5
    card = (await study_client.get("/api/reviews/due")).json()["cards"][0]
    await study_client.post(
        f"/api/reviews/cards/{card['id']}/rate", json={"rating": 3, "request_id": uuid.uuid4().hex}
    )
    clock.set(datetime(2026, 10, 6, 4, 59, tzinfo=UTC))  # 23:59 CDT, same local day
    assert (await study_client.get("/api/reviews/due")).json()["reviewed_today"] == 1
    clock.set(datetime(2026, 10, 6, 5, 1, tzinfo=UTC))  # 00:01 CDT on Oct 6
    assert (await study_client.get("/api/reviews/due")).json()["reviewed_today"] == 0
    await study_client.patch("/api/settings", json={"timezone": "UTC"})
    assert (await study_client.get("/api/reviews/due")).json()["reviewed_today"] == 1


async def test_cards_from_mistakes_and_notes_do_not_duplicate(study_client: AsyncClient) -> None:
    created = await study_client.post(
        "/api/reviews/cards",
        json={"source_kind": "mistake", "item_key": "q-3", "front_md": "Q3 stem", "back_md": "why"},
    )
    assert created.status_code == 201
    again = await study_client.post(
        "/api/reviews/cards",
        json={
            "source_kind": "mistake",
            "item_key": "q-3",
            "front_md": "different",
            "back_md": "text",
        },
    )
    assert again.status_code == 200 and again.json()["id"] == created.json()["id"]
    note = (await study_client.post("/api/notes", json={"body_md": "a note"})).json()
    from_note = await study_client.post(
        "/api/reviews/cards",
        json={"source_kind": "note", "note_id": note["id"], "front_md": "n", "back_md": "b"},
    )
    assert from_note.status_code == 201
    edited = await study_client.patch(
        f"/api/reviews/cards/{created.json()['id']}", json={"back_md": "edited"}
    )
    assert edited.json()["user_edited"] is True and edited.json()["back_md"] == "edited"
    listing = (await study_client.get("/api/reviews/cards")).json()
    assert listing["total"] == 5
    assert (
        await study_client.delete(f"/api/reviews/cards/{listing['cards'][0]['id']}")
    ).status_code in (200, 409)
