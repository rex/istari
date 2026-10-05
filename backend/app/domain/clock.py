"""Injectable clock so scheduling and analytics are testable with fixed time."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime:
        """Current time, timezone-aware UTC."""


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class FixedClock:
    """Test clock. `advance()` moves it forward deterministically."""

    def __init__(self, at: datetime) -> None:
        if at.tzinfo is None:
            raise ValueError("FixedClock needs a timezone-aware datetime")
        self._at = at.astimezone(UTC)

    def now(self) -> datetime:
        return self._at

    def set(self, at: datetime) -> None:
        self._at = at.astimezone(UTC)


def ensure_utc(value: datetime) -> datetime:
    """Normalise any aware datetime to UTC; reject naive values loudly."""
    if value.tzinfo is None:
        raise ValueError("naive datetime where an aware UTC datetime was required")
    return value.astimezone(UTC)
