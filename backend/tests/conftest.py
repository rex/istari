"""Shared fixtures: migrated test database, app with a fixed clock, logged-in client.

The test database is migrated with Alembic (so migrations are exercised), then
every table is truncated before each test.
"""

from __future__ import annotations

import os
import secrets
import shutil
import subprocess
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.adapters.db.engine import create_engine
from app.adapters.db.models import Base
from app.adapters.db.session import session_factory
from app.config import settings
from app.contracts.auth import OnboardingRequest
from app.domain.clock import FixedClock
from app.domain.content.validate import parse_pack
from app.main import create_app
from app.services import auth as auth_service
from app.services.content_import import import_pack
from app.services.settings import complete_onboarding
from tests.fixtures import mini_pack

TEST_URL = settings.test_database_url
OWNER_USERNAME = "pierce"
OWNER_PASSWORD = secrets.token_urlsafe(16)  # fresh per run; never a literal in the repo
FROZEN_NOW = datetime(2026, 10, 5, 20, 0, tzinfo=UTC)  # 15:00 CDT


@pytest.fixture(scope="session", autouse=True)
def migrated_schema() -> None:
    env = {**os.environ, "ALEMBIC_DATABASE_URL": TEST_URL}
    root = Path(__file__).resolve().parents[1]
    uv = shutil.which("uv")
    assert uv is not None, "uv must be on PATH to run the test suite"
    for args in (["downgrade", "base"], ["upgrade", "head"]):
        subprocess.run(  # noqa: S603 - fixed argv, test-only
            [uv, "run", "alembic", *args], cwd=root, env=env, check=True, capture_output=True
        )


@pytest_asyncio.fixture(scope="session")
async def engine() -> AsyncIterator[AsyncEngine]:
    engine = create_engine(TEST_URL, pool_size=3, max_overflow=3)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def clean_tables(engine: AsyncEngine) -> None:
    tables = ", ".join(f'"{t.name}"' for t in reversed(Base.metadata.sorted_tables))
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock(FROZEN_NOW)


@pytest_asyncio.fixture
async def db(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """A committing session for direct setup/assertions outside the app."""
    async with session_factory(engine)() as session:
        yield session
        await session.rollback()


@pytest.fixture
def app(engine: AsyncEngine, clock: FixedClock):  # type: ignore[no-untyped-def]
    return create_app(engine=engine, clock=clock)


@pytest_asyncio.fixture
async def client(app) -> AsyncIterator[AsyncClient]:  # type: ignore[no-untyped-def]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        yield ac


@pytest_asyncio.fixture
async def owner(engine: AsyncEngine) -> None:
    async with session_factory(engine)() as session, session.begin():
        await auth_service.create_owner(session, OWNER_USERNAME, OWNER_PASSWORD)


@pytest_asyncio.fixture
async def seeded(engine: AsyncEngine, clock: FixedClock) -> int:
    """Import the mini pack and complete onboarding. Returns the exam version id."""
    async with session_factory(engine)() as session, session.begin():
        report = await import_pack(session, parse_pack(mini_pack()), dry_run=False, now=clock.now())
        assert not report.track_changes
        exam_id = (await session.execute(text("SELECT id FROM exam_versions LIMIT 1"))).scalar_one()
        await complete_onboarding(
            session,
            OnboardingRequest(exam_version_id=exam_id, preferred_session_minutes=5),
            now=clock.now(),
        )
        return int(exam_id)


@pytest_asyncio.fixture
async def auth_client(client: AsyncClient, owner: None) -> AsyncClient:
    response = await client.post(
        "/api/auth/login", json={"username": OWNER_USERNAME, "password": OWNER_PASSWORD}
    )
    assert response.status_code == 200, response.text
    client.headers["x-csrf-token"] = response.json()["csrf_token"]
    return client


@pytest_asyncio.fixture
async def study_client(auth_client: AsyncClient, seeded: int) -> AsyncClient:
    """Logged in, content imported, onboarding done."""
    return auth_client
