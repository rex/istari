"""Watch: catalog from a learning root, streaming with Range, captions, progress."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine

from app.domain.clock import FixedClock
from app.main import create_app
from tests.conftest import OWNER_PASSWORD, OWNER_USERNAME

VIDEO = bytes(range(256)) * 40  # 10,240 bytes of "video"
SRT = (
    "1\n00:00:01,000 --> 00:00:03,500\nWelcome to the course.\n\n"
    "2\n00:00:03,500 --> 00:00:06,000\nLet us begin.\n"
)


@pytest.fixture
def learning_root(tmp_path: Path) -> Path:
    course = tmp_path / "Cloud" / "AWS" / "Some Course 2022 [SAA-C03]"
    (course / "01 - Intro").mkdir(parents=True)
    (course / "01 - Intro" / "001 Welcome.mp4").write_bytes(VIDEO)
    (course / "01 - Intro" / "001 Welcome_en.srt").write_text(SRT, encoding="utf-8")
    (course / "10 - EC2").mkdir()
    (course / "10 - EC2" / "002 Instance types.mp4").write_bytes(VIDEO[:512])
    (course / "02 - IAM").mkdir()
    (course / "02 - IAM" / "001 Users.mp4").write_bytes(VIDEO[:100])
    (course / "02 - IAM" / "Visit For More Courses.url").write_text("junk")
    (tmp_path / "Cloud" / "AWS" / "Not a course").mkdir()
    (tmp_path / "Cloud" / "AWS" / "Not a course" / "notes.txt").write_text("no video here")
    return tmp_path


@pytest_asyncio.fixture
async def watch_client(
    engine: AsyncEngine, clock: FixedClock, owner: None, learning_root: Path
) -> AsyncIterator[AsyncClient]:
    app = create_app(engine=engine, clock=clock, learning_root=learning_root)
    await app.state.catalog.refresh()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        response = await ac.post(
            "/api/auth/login", json={"username": OWNER_USERNAME, "password": OWNER_PASSWORD}
        )
        ac.headers["x-csrf-token"] = response.json()["csrf_token"]
        yield ac


async def test_catalog_lists_courses_with_sections_in_natural_order(
    watch_client: AsyncClient,
) -> None:
    listing = (await watch_client.get("/api/courses")).json()
    assert listing["status"]["configured"] is True and listing["status"]["course_count"] == 1
    [course] = listing["courses"]
    assert course["exam_code"] == "SAA-C03" and course["year"] == 2022
    assert (course["lecture_count"], course["caption_count"], course["completed_count"]) == (
        3,
        1,
        0,
    )

    detail = (await watch_client.get(f"/api/courses/{course['slug']}")).json()
    assert [s["title"] for s in detail["sections"]] == ["01 - Intro", "02 - IAM", "10 - EC2"]
    first = detail["sections"][0]["lectures"][0]
    assert first == {
        "path": "01 - Intro/001 Welcome.mp4",
        "title": "Welcome",
        "has_captions": True,
        "size_bytes": len(VIDEO),
        "progress": None,
    }
    assert (await watch_client.get("/api/courses/nope")).status_code == 404


async def test_media_streams_whole_file_and_byte_ranges(watch_client: AsyncClient) -> None:
    slug = (await watch_client.get("/api/courses")).json()["courses"][0]["slug"]
    url = f"/api/courses/{slug}/media"
    full = await watch_client.get(url, params={"path": "01 - Intro/001 Welcome.mp4"})
    assert full.status_code == 200 and full.content == VIDEO
    assert full.headers["content-type"] == "video/mp4"
    assert full.headers["accept-ranges"] == "bytes"

    part = await watch_client.get(
        url, params={"path": "01 - Intro/001 Welcome.mp4"}, headers={"Range": "bytes=10-19"}
    )
    assert part.status_code == 206 and part.content == VIDEO[10:20]
    assert part.headers["content-range"] == f"bytes 10-19/{len(VIDEO)}"

    # Only lectures the catalog reported resolve; nothing else on disk does.
    for bad in ("../../Cloud/AWS/Not a course/notes.txt", "01 - Intro/001 Welcome_en.srt", "x"):
        assert (await watch_client.get(url, params={"path": bad})).status_code == 404


async def test_captions_are_served_as_webvtt(watch_client: AsyncClient) -> None:
    slug = (await watch_client.get("/api/courses")).json()["courses"][0]["slug"]
    ok = await watch_client.get(
        f"/api/courses/{slug}/captions", params={"path": "01 - Intro/001 Welcome.mp4"}
    )
    assert ok.status_code == 200 and ok.headers["content-type"].startswith("text/vtt")
    assert ok.text.startswith("WEBVTT\n\n00:00:01.000 --> 00:00:03.500\nWelcome to the course.")
    none = await watch_client.get(
        f"/api/courses/{slug}/captions", params={"path": "10 - EC2/002 Instance types.mp4"}
    )
    assert none.status_code == 404


async def test_progress_round_trip_marks_completion_near_the_end(
    watch_client: AsyncClient,
) -> None:
    slug = (await watch_client.get("/api/courses")).json()["courses"][0]["slug"]
    saved = await watch_client.put(
        f"/api/courses/{slug}/progress",
        json={"lecture_path": "01 - Intro/001 Welcome.mp4", "position_seconds": 42.5},
    )
    assert saved.status_code == 200 and saved.json()["completed_at"] is None

    done = await watch_client.put(
        f"/api/courses/{slug}/progress",
        json={
            "lecture_path": "01 - Intro/001 Welcome.mp4",
            "position_seconds": 598,
            "duration_seconds": 600,
        },
    )
    assert done.json()["completed_at"] is not None

    listing = (await watch_client.get("/api/courses")).json()["courses"][0]
    assert listing["completed_count"] == 1 and listing["resume_title"] == "Welcome"
    detail = (await watch_client.get(f"/api/courses/{slug}")).json()
    first = detail["sections"][0]["lectures"][0]["progress"]
    assert first["position_seconds"] == 598 and detail["completed_count"] == 1

    unknown = await watch_client.put(
        f"/api/courses/{slug}/progress", json={"lecture_path": "nope.mp4", "position_seconds": 1}
    )
    assert unknown.status_code == 404
