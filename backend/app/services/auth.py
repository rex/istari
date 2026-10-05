"""Single-owner login: argon2id, server-side sessions, sliding-window throttling."""

from __future__ import annotations

import hashlib
import math
import secrets
from datetime import datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import AuthSession, LoginAttempt, Owner
from app.config import Settings
from app.domain.exceptions import AuthenticationError, ConflictError, ThrottledError

# argon2id with the library's current recommended defaults.
_hasher = PasswordHasher()

MIN_PASSWORD_LENGTH = 12
_TOUCH_INTERVAL = timedelta(minutes=5)


def hash_password(password: str) -> str:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ConflictError(f"password must be at least {MIN_PASSWORD_LENGTH} characters")
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return bool(_hasher.verify(password_hash, password))
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def get_owner(db: AsyncSession) -> Owner | None:
    return await db.scalar(select(Owner).limit(1))


async def create_owner(db: AsyncSession, username: str, password: str) -> Owner:
    if await get_owner(db) is not None:
        raise ConflictError("an owner already exists; use --reset-password to change it")
    owner = Owner(username=username.strip(), password_hash=hash_password(password))
    db.add(owner)
    await db.flush()
    return owner


async def set_owner_password(db: AsyncSession, username: str, password: str) -> Owner:
    owner = await db.scalar(select(Owner).where(Owner.username == username.strip()))
    if owner is None:
        raise ConflictError("no owner with that username")
    owner.password_hash = hash_password(password)
    owner.password_updated_at = datetime.now(tz=owner.created_at.tzinfo)
    await db.flush()
    return owner


async def _enforce_throttle(db: AsyncSession, username: str, now: datetime, cfg: Settings) -> None:
    window_start = now - timedelta(seconds=cfg.login_window_seconds)
    failures = await db.execute(
        select(func.count(LoginAttempt.id), func.max(LoginAttempt.attempted_at)).where(
            LoginAttempt.username == username,
            LoginAttempt.succeeded.is_(False),
            LoginAttempt.attempted_at >= window_start,
        )
    )
    count, last_failure = failures.one()
    if count >= cfg.login_max_attempts and last_failure is not None:
        unlock_at = last_failure + timedelta(seconds=cfg.login_lockout_seconds)
        remaining = (unlock_at - now).total_seconds()
        if remaining > 0:
            raise ThrottledError(
                "too many failed logins; try again later",
                details={"retry_after_seconds": math.ceil(remaining)},
            )


async def login(
    db: AsyncSession, username: str, password: str, *, now: datetime, cfg: Settings
) -> tuple[AuthSession, str]:
    """Verify credentials and open a session. Returns (row, raw cookie token)."""
    username = username.strip()[:64]
    await _enforce_throttle(db, username, now, cfg)
    owner = await db.scalar(select(Owner).where(Owner.username == username))
    ok = owner is not None and verify_password(owner.password_hash, password)
    db.add(LoginAttempt(username=username, succeeded=ok, attempted_at=now))
    if owner is None or not ok:
        await db.flush()
        raise AuthenticationError("invalid username or password")
    if _hasher.check_needs_rehash(owner.password_hash):
        owner.password_hash = _hasher.hash(password)
    raw = secrets.token_urlsafe(32)
    session = AuthSession(
        token_hash=_hash_token(raw),
        csrf_token=secrets.token_urlsafe(32),
        created_at=now,
        last_seen_at=now,
        expires_at=now + timedelta(hours=cfg.session_ttl_hours),
    )
    db.add(session)
    await db.flush()
    return session, raw


async def authenticate(db: AsyncSession, raw_token: str, *, now: datetime) -> AuthSession | None:
    session = await db.scalar(
        select(AuthSession).where(AuthSession.token_hash == _hash_token(raw_token))
    )
    if session is None or session.revoked_at is not None or session.expires_at <= now:
        return None
    if now - session.last_seen_at > _TOUCH_INTERVAL:
        session.last_seen_at = now
    return session


async def logout(db: AsyncSession, session: AuthSession, *, now: datetime) -> None:
    session.revoked_at = now
    await db.flush()
