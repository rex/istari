"""Lab attempts: what a verifier backend set up and graded, kept as the owner's evidence."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import LabAttempt
from app.contracts.lab_verifier import LabAttemptSummary, LabAttemptView
from app.domain.content.schemas.verifier import LabVerifierSpec
from app.domain.verifier import CheckResult, cap_output

ATTEMPT_HISTORY_LIMIT = 20


def _reason_line(row: LabAttempt) -> str:
    if row.checked_at is None:
        return ""
    return CheckResult(passed=bool(row.passed), output=row.output).reason_line


def attempt_view(row: LabAttempt) -> LabAttemptView:
    return LabAttemptView(
        id=row.id,
        setup_at=row.setup_at,
        checked_at=row.checked_at,
        passed=row.passed,
        output=row.output,
        reason_line=_reason_line(row),
        duration_seconds=row.duration_seconds,
    )


def attempt_summary(row: LabAttempt) -> LabAttemptSummary | None:
    if row.checked_at is None or row.passed is None:
        return None
    return LabAttemptSummary(
        checked_at=row.checked_at, passed=row.passed, reason_line=_reason_line(row)
    )


async def attempts_for(
    db: AsyncSession, item_id: int, *, limit: int = ATTEMPT_HISTORY_LIMIT
) -> list[LabAttempt]:
    """Newest first."""
    rows = await db.scalars(
        select(LabAttempt)
        .where(LabAttempt.item_id == item_id)
        .order_by(LabAttempt.created_at.desc(), LabAttempt.id.desc())
        .limit(limit)
    )
    return list(rows.all())


async def latest_graded_by_item(db: AsyncSession, item_ids: Iterable[int]) -> dict[int, LabAttempt]:
    ids = list(item_ids)
    if not ids:
        return {}
    rows = await db.scalars(
        select(LabAttempt)
        .where(LabAttempt.item_id.in_(ids), LabAttempt.checked_at.is_not(None))
        .order_by(LabAttempt.checked_at.desc(), LabAttempt.id.desc())
    )
    latest: dict[int, LabAttempt] = {}
    for row in rows.all():
        latest.setdefault(row.item_id, row)
    return latest


async def attempt_counts(db: AsyncSession, item_ids: Iterable[int]) -> dict[int, int]:
    ids = list(item_ids)
    if not ids:
        return {}
    rows = await db.execute(
        select(LabAttempt.item_id, func.count(LabAttempt.id))
        .where(LabAttempt.item_id.in_(ids))
        .group_by(LabAttempt.item_id)
    )
    return {int(item_id): int(count) for item_id, count in rows.all()}


async def _open_attempt(db: AsyncSession, item_id: int, question_id: str) -> LabAttempt | None:
    """The latest attempt that was set up but never checked, if any."""
    return await db.scalar(
        select(LabAttempt)
        .where(
            LabAttempt.item_id == item_id,
            LabAttempt.question_id == question_id,
            LabAttempt.checked_at.is_(None),
        )
        .order_by(LabAttempt.created_at.desc(), LabAttempt.id.desc())
        .limit(1)
    )


async def latest_attempt_run(db: AsyncSession, item_id: int, question_id: str) -> str | None:
    """The backend run of the newest attempt, checked or not: what a re-check grades on a
    backend whose every setup makes a fresh run (LocalEmu names the run's resources)."""
    return await db.scalar(
        select(LabAttempt.k16s_session_id)
        .where(
            LabAttempt.item_id == item_id,
            LabAttempt.question_id == question_id,
            LabAttempt.k16s_session_id.is_not(None),
        )
        .order_by(LabAttempt.created_at.desc(), LabAttempt.id.desc())
        .limit(1)
    )


async def record_setup(
    db: AsyncSession,
    *,
    item_id: int,
    spec: LabVerifierSpec,
    session_id: str,
    output: str,
    now: datetime,
) -> LabAttempt:
    row = LabAttempt(
        item_id=item_id,
        backend=spec.backend,
        profile=spec.profile,
        question_id=spec.question,
        k16s_session_id=session_id,
        setup_at=now,
        output=cap_output(output),
    )
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return row


async def record_check(
    db: AsyncSession,
    *,
    item_id: int,
    spec: LabVerifierSpec,
    session_id: str,
    passed: bool,
    output: str,
    now: datetime,
) -> LabAttempt:
    """Grade the open attempt, or a fresh one when the check ran without a setup."""
    row = await _open_attempt(db, item_id, spec.question)
    if row is None:
        row = LabAttempt(
            item_id=item_id,
            backend=spec.backend,
            profile=spec.profile,
            question_id=spec.question,
            k16s_session_id=session_id,
        )
        db.add(row)
    row.checked_at = now
    row.passed = passed
    row.output = cap_output(output)
    if row.setup_at is not None:
        row.duration_seconds = max(0, int((now - row.setup_at).total_seconds()))
    await db.flush()
    await db.refresh(row)
    return row
