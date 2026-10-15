"""A stand-in for the K16S exam server: the seven endpoints with canned, controllable data.

The shape follows K16S's `server/handlers.go` (one active session; setup and check need
one; `unavailable` under lightweight mode for `requires: heavy`). Every string here is
ours; nothing is copied from the real question bank, which is not ours to redistribute.

Runs in-process for the integration tests (`httpx.ASGITransport`) and standalone for the
Playwright suite: `uv run uvicorn tests.k16s_stub:app --port 8081`.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

QUESTIONS: dict[str, list[dict[str, object]]] = {
    "cka": [
        {
            "id": "stub-01-crashloop",
            "title": "Stub: a pod keeps crashing",
            "weight": 4,
            "context": "Namespace stub-apps, pod web-0 restarts every few seconds.",
            "description": "Find out why the pod crashes and make it stay Running.\n"
            "Do not delete the namespace.",
            "hint": "Look at the container's last termination reason.",
        },
        {
            "id": "stub-03-passing",
            "title": "Stub: already done",
            "weight": 5,
            "context": "",
            "description": "A task whose validate script passes immediately.",
            "hint": "",
        },
    ],
    "cka2": [
        {
            "id": "stub-02-heavy",
            "title": "Stub: needs the full install",
            "weight": 6,
            "context": "",
            "description": "A task that only runs on the VM-based install.",
            "hint": "",
            "requires": "heavy",
        },
    ],
}

UNAVAILABLE_REASON = (
    "This task needs the full VM-based install; its environment cannot be created under "
    "the lightweight mode."
)


@dataclass
class StubState:
    mode: str = "full"
    # question id -> whether check passes; unknown ids fail.
    results: dict[str, bool] = field(default_factory=lambda: {"stub-03-passing": True})
    # Extra latency injected into setup and check, to exercise client timeouts.
    delay_seconds: float = 0.0
    session: dict[str, object] | None = None
    session_starts: int = 0
    question_fetches: int = 0
    setups: list[str] = field(default_factory=list)
    checks: list[str] = field(default_factory=list)
    # Replaces the module's bank when set: the mapping tests serve a pack's real ids with
    # placeholder text of our own.
    questions: dict[str, list[dict[str, object]]] | None = None

    def reset(self) -> None:
        self.__init__()  # type: ignore[misc]


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _find(
    bank: dict[str, list[dict[str, object]]], profile: str, question_id: str
) -> dict[str, object] | None:
    return next((q for q in bank.get(profile, []) if q["id"] == question_id), None)


def placeholder_bank(
    ids_by_profile: dict[str, list[str]],
) -> dict[str, list[dict[str, object]]]:
    """A bank that serves the given ids with placeholder text of our own, for mapping tests."""
    return {
        profile: [
            {
                "id": question_id,
                "title": f"Stub task {question_id}",
                "weight": 4,
                "context": "",
                "description": "Placeholder text; a real instance serves its own.",
                "hint": "",
            }
            for question_id in ids
        ]
        for profile, ids in ids_by_profile.items()
    }


def create_stub() -> FastAPI:
    app = FastAPI(title="k16s-stub")
    state = StubState()
    app.state.stub = state

    def bank() -> dict[str, list[dict[str, object]]]:
        return state.questions if state.questions is not None else QUESTIONS

    def error(code: int, message: str) -> JSONResponse:
        return JSONResponse(status_code=code, content={"error": message})

    def unavailable(question: dict[str, object] | None) -> bool:
        return state.mode == "lightweight" and bool(
            question and question.get("requires") == "heavy"
        )

    @app.get("/api/status")
    async def status() -> dict[str, object]:
        return {
            "ok": True,
            "session": state.session,
            "profiles": list(bank()),
            "mode": state.mode,
        }

    @app.get("/api/session", response_model=None)
    async def get_session() -> JSONResponse | dict[str, object]:
        if state.session is None:
            return error(404, "no active session")
        return state.session

    @app.post("/api/session/start", response_model=None)
    async def start_session(request: Request) -> JSONResponse | dict[str, object]:
        body = await request.json()
        profile = str(body.get("profile") or "cka")
        if profile not in bank():
            return error(400, f"unknown profile: {profile}")
        state.session_starts += 1
        state.session = {
            "id": uuid.uuid4().hex,
            "profile": profile,
            "started_at": _now(),
            "ended_at": None,
            "duration_secs": int(body.get("duration_secs") or 7200),
            "progress": {},
        }
        return {"session": state.session}

    @app.post("/api/session/end", response_model=None)
    async def end_session() -> JSONResponse | dict[str, object]:
        if state.session is None:
            return error(404, "no active session")
        state.session["ended_at"] = _now()
        ended, state.session = state.session, None
        return {"session": ended}

    @app.get("/api/questions", response_model=None)
    async def questions(profile: str = "cka") -> JSONResponse | dict[str, object]:
        if profile not in bank():
            return error(404, f"unknown profile: {profile}")
        state.question_fetches += 1
        return {"questions": bank()[profile]}

    @app.post("/api/questions/{question_id}/setup", response_model=None)
    async def setup(question_id: str) -> JSONResponse | dict[str, object]:
        if state.session is None:
            return error(400, "no active session")
        question = _find(bank(), str(state.session["profile"]), question_id)
        if unavailable(question):
            return {"unavailable": True, "reason": UNAVAILABLE_REASON}
        if state.delay_seconds:
            await asyncio.sleep(state.delay_seconds)
        state.setups.append(question_id)
        return {"ok": True, "output": f"[stub] environment ready for {question_id}\n"}

    @app.post("/api/questions/{question_id}/check", response_model=None)
    async def check(question_id: str) -> JSONResponse | dict[str, object]:
        if state.session is None:
            return error(400, "no active session")
        question = _find(bank(), str(state.session["profile"]), question_id)
        if question is None:
            return error(404, f"question not found: {question_id}")
        if unavailable(question):
            return {"unavailable": True, "reason": UNAVAILABLE_REASON}
        if state.delay_seconds:
            await asyncio.sleep(state.delay_seconds)
        state.checks.append(question_id)
        passed = state.results.get(question_id, False)
        line = (
            "PASS: the task is complete" if passed else "FAIL: pod web-0 is still CrashLoopBackOff"
        )
        return {"passed": passed, "output": f"[stub] checking {question_id}\n{line}\n"}

    return app


app = create_stub()
