"""Verified labs: the verifier's live state, and the attempts it has graded."""

from __future__ import annotations

from datetime import datetime

from app.contracts.common import ApiModel


class LabVerifierSpecView(ApiModel):
    backend: str
    profile: str
    question: str
    weight: int
    time_limit_minutes: int | None


class LabAttemptView(ApiModel):
    id: int
    setup_at: datetime | None
    checked_at: datetime | None
    # None until the check has run.
    passed: bool | None
    output: str
    # The grader's verdict line (the last non-empty line of its output); empty until checked.
    reason_line: str
    duration_seconds: int | None


class LabAttemptSummary(ApiModel):
    """What a lab card shows: the latest graded attempt."""

    checked_at: datetime
    passed: bool
    reason_line: str


class VerifierTaskView(ApiModel):
    """The task as the backend states it, fetched live and shown with attribution, never stored."""

    title: str
    context: str
    description: str
    hint: str
    weight: int
    requires: str


class VerifierStateView(ApiModel):
    spec: LabVerifierSpecView
    configured: bool
    reachable: bool
    mode: str | None
    # The instance serves this lab's profile.
    profile_available: bool
    # The instance's active session profile, so the page can say when a setup will switch it.
    session_profile: str | None
    terminal_url: str | None
    exam_url: str | None
    map_url: str | None
    # Environment lines for the learner's own shell (LocalEmu: endpoint, identity, region);
    # empty when the work happens in the backend's terminal.
    cli_env: list[str]
    task: VerifierTaskView | None
    # Set when the task cannot run in the instance's current mode.
    unavailable_reason: str | None
    # One sentence when something stands in the way (not configured, unreachable, unknown task).
    message: str | None
    attribution: str
    attempts: list[LabAttemptView]
    last_attempt: LabAttemptView | None


class SetupResponse(ApiModel):
    ok: bool
    output: str
    unavailable_reason: str | None
    attempt: LabAttemptView | None


class CheckResponse(ApiModel):
    passed: bool
    output: str
    reason_line: str
    unavailable_reason: str | None
    attempt: LabAttemptView | None
