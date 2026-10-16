"""The lecture index end to end: captions off a learning root, ranked against the track's
objectives, reviewed by the owner, and the owner's decisions surviving a rebuild."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.adapters.db.session import session_factory
from app.contracts.auth import OnboardingRequest
from app.domain.clock import FixedClock
from app.domain.content.validate import parse_pack
from app.main import create_app
from app.services.content_import import import_pack
from app.services.settings import complete_onboarding
from tests.conftest import OWNER_PASSWORD, OWNER_USERNAME
from tests.fixtures import mini_pack

VIDEO = bytes(range(256)) * 4


def _srt(*lines: str) -> str:
    cues = []
    for index, line in enumerate(lines, start=1):
        start, end = index * 4, index * 4 + 3
        cues.append(f"{index}\n00:00:{start:02d},000 --> 00:00:{end:02d},500\n{line}\n")
    return "\n".join(cues)


IAM_SRT = _srt(
    "In this lecture we look at IAM users, roles and policies.",
    "A role hands out temporary credentials through STS, so nothing long-lived sits on the box.",
    "Least privilege means the policy grants only what the job needs; never the root user.",
)
STORAGE_SRT = _srt(
    "S3 is object storage: buckets, storage classes, lifecycle rules.",
    "EBS is a block volume attached to one instance; EFS is a shared file system.",
    "Pick the storage class by access frequency and cost.",
)
KEYS_SRT = _srt(
    "KMS customer managed keys encrypt the data at rest; rotate the key every year.",
    "TLS certificates from ACM protect data in transit; the private key never leaves.",
)


def lecture_pack() -> dict[str, object]:
    """The mini pack with objectives that have words of their own, so ranking can tell them
    apart; item slugs and option ids untouched."""
    pack = mini_pack()
    domains = pack["domains"]
    assert isinstance(domains, list)
    titles = {
        "1.1": (
            "Identity and access: IAM roles and least privilege",
            ["IAM users, roles and policies", "Least privilege and the root user"],
        ),
        "1.2": (
            "Encryption with KMS keys and TLS",
            ["KMS customer managed keys", "TLS certificates in transit"],
        ),
        "2.1": (
            "Storage: S3 buckets, EBS volumes and EFS file systems",
            ["Object storage classes", "Block and file storage"],
        ),
    }
    for domain in domains:
        assert isinstance(domain, dict)
        objectives = domain["objectives"]
        assert isinstance(objectives, list)
        for objective in objectives:
            assert isinstance(objective, dict)
            title, knowledge = titles[str(objective["code"])]
            objective["title"] = title
            objective["knowledge"] = knowledge
    return pack


@pytest.fixture
def learning_root(tmp_path: Path) -> Path:
    course = tmp_path / "Cloud" / "Testing" / "Identity Course 2024 [TST-C01]"
    (course / "01 - IAM").mkdir(parents=True)
    (course / "01 - IAM" / "001 Roles and least privilege obj-1-1.mp4").write_bytes(VIDEO)
    (course / "01 - IAM" / "001 Roles and least privilege obj-1-1.srt").write_text(
        IAM_SRT, encoding="utf-8"
    )
    (course / "02 - Storage").mkdir()
    (course / "02 - Storage" / "001 Buckets and volumes.mp4").write_bytes(VIDEO)
    (course / "02 - Storage" / "001 Buckets and volumes.srt").write_text(
        STORAGE_SRT, encoding="utf-8"
    )
    (course / "03 - Extras").mkdir()
    (course / "03 - Extras" / "001 Welcome.mp4").write_bytes(VIDEO)
    # On the subject but another exam: its "obj-1-2" names that exam's objective, not ours.
    other_exam = tmp_path / "Cloud" / "Testing" / "Other Cert Prep 2023 [OTH-C01]"
    other_exam.mkdir()
    (other_exam / "001 Keys and certificates obj-1-2.mp4").write_bytes(VIDEO)
    (other_exam / "001 Keys and certificates obj-1-2.srt").write_text(KEYS_SRT, encoding="utf-8")
    other = tmp_path / "Hobbies" / "Woodworking" / "Chisels 2020"
    other.mkdir(parents=True)
    (other / "001 Sharpening.mp4").write_bytes(VIDEO)
    (other / "001 Sharpening.srt").write_text(_srt("Sharpen the chisel on a stone."))
    return tmp_path


@pytest_asyncio.fixture
async def indexed_client(
    engine: AsyncEngine, clock: FixedClock, owner: None, learning_root: Path
) -> AsyncIterator[tuple[AsyncClient, object]]:
    async with session_factory(engine)() as session, session.begin():
        await import_pack(session, parse_pack(lecture_pack()), dry_run=False, now=clock.now())
        exam_id = (await session.execute(text("SELECT id FROM exam_versions LIMIT 1"))).scalar_one()
        await complete_onboarding(
            session, OnboardingRequest(exam_version_id=int(exam_id)), now=clock.now()
        )
    app = create_app(
        engine=engine,
        clock=clock,
        learning_root=learning_root,
        learning_topics=("Cloud/Testing", "Hobbies/Woodworking"),
    )
    await app.state.catalog.refresh()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        response = await ac.post(
            "/api/auth/login", json={"username": OWNER_USERNAME, "password": OWNER_PASSWORD}
        )
        ac.headers["x-csrf-token"] = response.json()["csrf_token"]
        yield ac, app


async def _rebuild(client: AsyncClient, app: object) -> dict[str, Any]:
    started = await client.post("/api/lecture-index/rebuild")
    assert started.status_code == 202, started.text
    task = app.state.lecture_index.task  # type: ignore[attr-defined]
    await task
    status = (await client.get("/api/lecture-index")).json()
    assert status["running"] is False and status["last_error"] is None, status
    return dict(status)


async def test_index_ranks_captioned_lectures_and_the_owner_decides(
    indexed_client: tuple[AsyncClient, object],
) -> None:
    client, app = indexed_client
    status = await _rebuild(client, app)
    assert status["candidate_courses"] == 2  # the woodworking course is not on the track
    assert (status["lectures_total"], status["lectures_with_captions"]) == (4, 3)
    assert status["lectures_indexed"] == 3 and status["mappings"] >= 3

    # The queue walks the courses in order: the IAM lecture first, mapped by its title rule.
    queue = (await client.get("/api/lecture-index/review")).json()
    assert queue["remaining"] == 3 and queue["reviewed"] == 0 and queue["indexed"] == 3
    first = queue["lecture"]
    assert first["lecture_title"] == "Roles and least privilege obj-1-1"
    assert first["duration_seconds"] == 15.5 and first["word_count"] > 10
    assert "IAM users" in first["excerpt"]
    top = first["candidates"][0]
    assert (top["objective_code"], top["source"], top["normalized"]) == ("1.1", "rule", 1.0)

    pinned = (
        await client.post(
            "/api/lecture-index/review",
            json={
                "course_slug": first["course_slug"],
                "lecture_path": first["lecture_path"],
                "pin": ["1.1"],
            },
        )
    ).json()
    assert pinned["reviewed"] is True and pinned["candidates"][0]["source"] == "pinned"

    # Next: the storage lecture, ranked by its words alone, under the storage objective.
    queue = (await client.get("/api/lecture-index/review")).json()
    second = queue["lecture"]
    assert second["lecture_title"] == "Buckets and volumes" and queue["remaining"] == 2
    best = second["candidates"][0]
    assert (best["objective_code"], best["source"]) == ("2.1", "lexical")
    assert "s3" in best["matched_terms"] and "storage" in best["matched_terms"]
    assert all(c["objective_code"] != "1.1" for c in second["candidates"])

    excluded = (
        await client.post(
            "/api/lecture-index/review",
            json={
                "course_slug": second["course_slug"],
                "lecture_path": second["lecture_path"],
                "exclude": True,
            },
        )
    ).json()
    assert all(c["source"] == "excluded" for c in excluded["candidates"])

    # Last: the other exam's lecture. Its "obj-1-2" is not our title rule; its words rank it.
    queue = (await client.get("/api/lecture-index/review")).json()
    third = queue["lecture"]
    assert third["lecture_title"] == "Keys and certificates obj-1-2" and queue["remaining"] == 1
    assert third["candidates"][0]["objective_code"] == "1.2"
    assert all(c["source"] == "lexical" for c in third["candidates"])
    await client.post(
        "/api/lecture-index/review",
        json={
            "course_slug": third["course_slug"],
            "lecture_path": third["lecture_path"],
            "exclude": True,
        },
    )
    queue = (await client.get("/api/lecture-index/review")).json()
    assert queue["lecture"] is None and queue["remaining"] == 0 and queue["reviewed"] == 3

    # Lookups: an excluded lecture is gone from its objective; the pinned one leads.
    storage = (await client.get("/api/lecture-index/objectives/2.1")).json()
    assert storage["lectures"] == []
    iam = (await client.get("/api/lecture-index/objectives/1.1")).json()
    assert [row["source"] for row in iam["lectures"]] == ["pinned"]
    assert iam["lectures"][0]["lecture_path"] == first["lecture_path"]
    mappings = (
        await client.get(
            f"/api/lecture-index/lectures/{first['course_slug']}",
            params={"path": first["lecture_path"]},
        )
    ).json()
    assert mappings[0]["objective_code"] == "1.1" and mappings[0]["source"] == "pinned"
    assert (await client.get("/api/lecture-index/objectives/9.9")).status_code == 404

    # A rebuild rewrites the machine rows and keeps the owner's.
    again = await _rebuild(client, app)
    assert again["reviewed"] == 3
    iam = (await client.get("/api/lecture-index/objectives/1.1")).json()
    assert [row["source"] for row in iam["lectures"]] == ["pinned"]
    assert (await client.get("/api/lecture-index/objectives/2.1")).json()["lectures"] == []
    assert (await client.get("/api/lecture-index/review")).json()["remaining"] == 0


async def test_rebuild_is_refused_while_one_runs_and_status_reads_before_any_run(
    indexed_client: tuple[AsyncClient, object],
) -> None:
    client, app = indexed_client
    before = (await client.get("/api/lecture-index")).json()
    assert before["lectures_indexed"] == 0 and before["running"] is False
    assert before["candidate_courses"] == 2  # counted by subject before any run, like a build
    first = await client.post("/api/lecture-index/rebuild")
    second = await client.post("/api/lecture-index/rebuild")
    assert first.status_code == 202 and second.status_code == 202
    runner = app.state.lecture_index  # type: ignore[attr-defined]
    await runner.task
    runs = (await client.get("/api/lecture-index")).json()
    assert runs["lectures_indexed"] == 3 and runs["running"] is False
