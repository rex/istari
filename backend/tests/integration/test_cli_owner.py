"""The owner bootstrap the CLI and the container entrypoint share."""

from __future__ import annotations

import secrets

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.cli.owner import bootstrap_owner
from app.domain.exceptions import ConflictError
from app.services import auth as auth_service


async def test_if_missing_creates_once_and_then_leaves_the_owner_alone(db: AsyncSession) -> None:
    first_password = secrets.token_urlsafe(16)
    assert await bootstrap_owner(db, "pierce", first_password, if_missing=True) == (
        "owner pierce created"
    )
    # A restart with different values (or a later rename in the vault) changes nothing.
    report = await bootstrap_owner(db, "someone-else", secrets.token_urlsafe(16), if_missing=True)
    assert report == "owner pierce already exists; nothing to do"
    owner = await auth_service.get_owner(db)
    assert owner is not None and owner.username == "pierce"
    assert auth_service.verify_password(owner.password_hash, first_password)


async def test_without_the_flag_a_second_owner_is_a_conflict(db: AsyncSession) -> None:
    await bootstrap_owner(db, "pierce", secrets.token_urlsafe(16))
    with pytest.raises(ConflictError):
        await bootstrap_owner(db, "pierce", secrets.token_urlsafe(16))


async def test_reset_password_rotates_the_existing_owner(db: AsyncSession) -> None:
    await bootstrap_owner(db, "pierce", secrets.token_urlsafe(16))
    new_password = secrets.token_urlsafe(16)
    report = await bootstrap_owner(db, "pierce", new_password, reset_password=True)
    assert report == "password updated for pierce"
    owner = await auth_service.get_owner(db)
    assert owner is not None and auth_service.verify_password(owner.password_hash, new_password)
