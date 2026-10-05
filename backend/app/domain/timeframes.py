"""Local-day arithmetic. Storage is UTC; "today" is defined in the user's timezone."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.domain.exceptions import ValidationError


def resolve_timezone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValidationError(f"unknown timezone: {name}") from exc


def local_day_bounds(now: datetime, tz_name: str) -> tuple[datetime, datetime]:
    """UTC [start, end) of the local calendar day containing `now`."""
    tz = resolve_timezone(tz_name)
    local = now.astimezone(tz)
    start_local = local.replace(hour=0, minute=0, second=0, microsecond=0)
    end_local = start_local + timedelta(days=1)
    return start_local.astimezone(UTC), end_local.astimezone(UTC)


def local_date(at: datetime, tz_name: str) -> date:
    return at.astimezone(resolve_timezone(tz_name)).date()


def format_local(at: datetime, tz_name: str) -> str:
    """ISO-8601 with offset, in the user's zone — what the UI renders."""
    return at.astimezone(resolve_timezone(tz_name)).isoformat(timespec="minutes")


def days_until(target: date, now: datetime, tz_name: str) -> int:
    return (target - local_date(now, tz_name)).days
