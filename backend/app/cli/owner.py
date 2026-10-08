"""Owner bootstrap shared by the CLI and the container entrypoint."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.services import auth as auth_service


async def bootstrap_owner(
    db: AsyncSession,
    username: str,
    password: str,
    *,
    reset_password: bool = False,
    if_missing: bool = False,
) -> str:
    """Create the owner, rotate the password, or leave an existing owner alone.

    Returns a one-line report for the operator. ``if_missing`` makes the call
    idempotent, which is what a container entrypoint needs: when an owner already
    exists it is kept, whoever it is, and nothing is written. Without it a second
    owner is a conflict, as before.
    """
    if reset_password:
        await auth_service.set_owner_password(db, username, password)
        return f"password updated for {username}"
    if if_missing:
        existing = await auth_service.get_owner(db)
        if existing is not None:
            return f"owner {existing.username} already exists; nothing to do"
    await auth_service.create_owner(db, username, password)
    return f"owner {username} created"
