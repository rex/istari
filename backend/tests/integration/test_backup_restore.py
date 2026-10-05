"""Backup + restore into an isolated database, using the real scripts and pg tools."""

from __future__ import annotations

import os
import shutil
import subprocess
import uuid
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings

ROOT = Path(__file__).resolve().parents[2].parent
RESTORE_DB = "istari_restore_test"

pytestmark = pytest.mark.skipif(
    shutil.which("pg_dump") is None or shutil.which("pg_restore") is None,
    reason="pg_dump/pg_restore not on PATH — install PostgreSQL client tools to run this",
)


def _run(script: str, *args: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed argv, test-only
        [str(ROOT / "scripts" / script), *args],
        env={**os.environ, **env},
        check=True,
        capture_output=True,
        text=True,
    )


async def test_backup_then_restore_preserves_history_and_active_session(
    study_client: AsyncClient, tmp_path: Path
) -> None:
    # Learning history + an in-progress session with a draft.
    session = (
        await study_client.post("/api/sessions", json={"kind": "practice", "minutes": 5})
    ).json()
    await study_client.post(
        f"/api/sessions/{session['id']}/items/1/answer",
        json={"selected_option_ids": ["o1"], "request_id": uuid.uuid4().hex},
    )
    await study_client.put(
        f"/api/sessions/{session['id']}/items/2/draft",
        json={"selected_option_ids": ["o3"], "expected_version": 2},
    )
    await study_client.post("/api/notes", json={"item_key": "q-1", "body_md": "private note"})

    env = {"DATABASE_URL": settings.test_database_url, "BACKUP_DIR": str(tmp_path)}
    backup = _run("backup.sh", env=env)
    dump = next(tmp_path.glob("istari-*.dump"))  # noqa: ASYNC240 - test-only, one tiny listing
    assert "backup written" in backup.stdout and dump.stat().st_size > 0
    assert oct(dump.stat().st_mode)[-3:] == "600"

    _run("restore.sh", str(dump), env={**env, "TARGET_DB": RESTORE_DB})

    restored_url = settings.test_database_url.rsplit("/", 1)[0] + f"/{RESTORE_DB}"
    engine = create_async_engine(restored_url)
    try:
        async with engine.connect() as conn:
            answers = (await conn.execute(text("SELECT count(*) FROM answers"))).scalar_one()
            notes = (await conn.execute(text("SELECT body_md FROM notes"))).scalars().all()
            active = (
                await conn.execute(
                    text("SELECT status, version FROM study_sessions WHERE id = :id"),
                    {"id": session["id"]},
                )
            ).one()
            draft = (
                await conn.execute(
                    text(
                        "SELECT draft_selection FROM session_items "
                        "WHERE session_id = :id AND position = 2"
                    ),
                    {"id": session["id"]},
                )
            ).scalar_one()
            owner = (await conn.execute(text("SELECT count(*) FROM owner"))).scalar_one()
    finally:
        await engine.dispose()
    assert answers == 1 and notes == ["private note"] and owner == 1
    assert tuple(active) == ("in_progress", 3)
    assert draft == ["o3"]
