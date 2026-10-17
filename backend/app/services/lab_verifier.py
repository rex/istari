"""Verified labs: the backend's live state for a lab, and setting up and checking it there.

Nothing here provisions anything. The backend (K16S, or the LocalEmu AWS emulator) runs on
the owner's own machine or VM; Istari asks it to set a task up, lets the owner work in its
terminal or their own shell, asks it to grade, and keeps the verdict as an attempt. The lab's
spec names the backend, and its client comes from the configured ones.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from functools import partial

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import ContentItem, ContentRevision
from app.contracts.lab_verifier import (
    CheckResponse,
    LabVerifierSpecView,
    SetupResponse,
    VerifierStateView,
    VerifierTaskView,
)
from app.domain.content.schemas.verifier import LabVerifierSpec
from app.domain.exceptions import ConflictError, NotFoundError, UpstreamError
from app.domain.verifier import VerifierQuestion, VerifierStatus
from app.services.content_query import get_item
from app.services.lab_attempts import (
    attempt_view,
    attempts_for,
    latest_attempt_run,
    record_check,
    record_setup,
)
from app.services.verifier_clients import (
    VerifierClient,
    VerifierClients,
    attribution,
    unconfigured_message,
)

log = logging.getLogger("istari.labs")

HEAVY_IN_LIGHTWEIGHT = (
    "This task needs the full VM-based install; the instance runs in lightweight mode."
)


def verifier_spec(rev: ContentRevision) -> LabVerifierSpec | None:
    raw = rev.content.get("verifier")
    if not isinstance(raw, dict):
        return None
    return LabVerifierSpec.model_validate(raw)


def spec_view(spec: LabVerifierSpec) -> LabVerifierSpecView:
    return LabVerifierSpecView(
        backend=spec.backend,
        profile=spec.profile,
        question=spec.question,
        weight=spec.weight,
        time_limit_minutes=spec.time_limit_minutes,
    )


def _task_view(question: VerifierQuestion) -> VerifierTaskView:
    return VerifierTaskView(
        title=question.title,
        context=question.context,
        description=question.description,
        hint=question.hint,
        weight=question.weight,
        requires=question.requires,
    )


async def _require_verified(
    db: AsyncSession, key: str
) -> tuple[ContentItem, ContentRevision, LabVerifierSpec]:
    item, rev = await get_item(db, key, kind="lab")
    spec = verifier_spec(rev)
    if spec is None:
        raise NotFoundError(f"lab '{key}' has no verifier; it is done by hand")
    return item, rev, spec


def _require_client(clients: VerifierClients, backend: str) -> VerifierClient:
    client = clients.get(backend)
    if client is None:
        raise ConflictError(
            unconfigured_message(backend), details={"code": f"{backend}_unconfigured"}
        )
    return client


def _unavailable(question: VerifierQuestion | None, status: VerifierStatus) -> str | None:
    if question is not None and question.requires == "heavy" and status.mode == "lightweight":
        return HEAVY_IN_LIGHTWEIGHT
    return None


async def state(
    db: AsyncSession, *, key: str, clients: VerifierClients, headlamp_url: str
) -> VerifierStateView:
    item, _rev, spec = await _require_verified(db, key)
    attempts = [attempt_view(row) for row in await attempts_for(db, item.id)]
    client = clients.get(spec.backend)
    view = partial(
        VerifierStateView,
        spec=spec_view(spec),
        attribution=attribution(spec.backend),
        attempts=attempts,
        last_attempt=next((a for a in attempts if a.checked_at is not None), None),
        # The cluster map belongs to the K16S cluster; other backends have none.
        map_url=(headlamp_url or None) if spec.backend == "k16s" else None,
        cli_env=list(client.cli_env) if client is not None else [],
    )
    if client is None:
        return view(
            configured=False,
            reachable=False,
            mode=None,
            profile_available=False,
            session_profile=None,
            terminal_url=None,
            exam_url=None,
            task=None,
            unavailable_reason=None,
            message=unconfigured_message(spec.backend),
        )
    try:
        status = await client.status()
        question = (
            await client.question(spec.profile, spec.question)
            if spec.profile in status.profiles
            else None
        )
    except UpstreamError as exc:
        return view(
            configured=True,
            reachable=False,
            mode=None,
            profile_available=False,
            session_profile=None,
            terminal_url=client.terminal_url,
            exam_url=client.exam_url,
            task=None,
            unavailable_reason=None,
            message=exc.message,
        )
    profile_available = spec.profile in status.profiles
    message: str | None = None
    if not profile_available:
        served = ", ".join(status.profiles) or "none"
        message = f"The instance does not serve the '{spec.profile}' profile (it serves: {served})."
    elif question is None:
        message = f"The instance's '{spec.profile}' profile has no question '{spec.question}'."
    active = status.session if status.session is not None and status.session.active else None
    return view(
        configured=True,
        reachable=True,
        mode=status.mode,
        profile_available=profile_available,
        session_profile=active.profile if active else None,
        terminal_url=client.terminal_url,
        exam_url=client.exam_url,
        task=_task_view(question) if question is not None else None,
        unavailable_reason=_unavailable(question, status),
        message=message,
    )


def _log(event: str, key: str, spec: LabVerifierSpec, result: str, started: float) -> None:
    log.info(
        event,
        extra={
            "event": event,
            "lab": key,
            "question": spec.question,
            "profile": spec.profile,
            "result": result,
            "duration_ms": round((time.perf_counter() - started) * 1000, 1),
        },
    )


async def setup(
    db: AsyncSession, *, key: str, clients: VerifierClients, now: datetime
) -> SetupResponse:
    item, _rev, spec = await _require_verified(db, key)
    backend = _require_client(clients, spec.backend)
    started = time.perf_counter()
    session = await backend.ensure_session(spec.profile)
    result = await backend.setup(spec.question, run=session.id)
    if result.unavailable_reason is not None:
        _log("lab.setup", key, spec, "unavailable", started)
        return SetupResponse(
            ok=False, output="", unavailable_reason=result.unavailable_reason, attempt=None
        )
    row = await record_setup(
        db, item_id=item.id, spec=spec, session_id=session.id, output=result.output, now=now
    )
    _log("lab.setup", key, spec, "ok" if result.ok else "failed", started)
    return SetupResponse(
        ok=result.ok, output=row.output, unavailable_reason=None, attempt=attempt_view(row)
    )


async def check(
    db: AsyncSession, *, key: str, clients: VerifierClients, now: datetime
) -> CheckResponse:
    item, _rev, spec = await _require_verified(db, key)
    backend = _require_client(clients, spec.backend)
    started = time.perf_counter()
    session = await backend.ensure_session(spec.profile)
    # K16S grades its live session. LocalEmu grades the run the latest setup made, so a
    # re-check after a fix grades the same resources; with no setup there is no run to grade.
    run = session.id
    if backend.per_attempt_runs:
        run = await latest_attempt_run(db, item.id, spec.question) or ""
    result = await backend.check(spec.question, run=run)
    if result.unavailable_reason is not None:
        _log("lab.check", key, spec, "unavailable", started)
        return CheckResponse(
            passed=False,
            output="",
            reason_line="",
            unavailable_reason=result.unavailable_reason,
            attempt=None,
        )
    row = await record_check(
        db,
        item_id=item.id,
        spec=spec,
        session_id=run,
        passed=result.passed,
        output=result.output,
        now=now,
    )
    _log("lab.check", key, spec, "passed" if result.passed else "failed", started)
    view = attempt_view(row)
    return CheckResponse(
        passed=result.passed,
        output=view.output,
        reason_line=view.reason_line,
        unavailable_reason=None,
        attempt=view,
    )
