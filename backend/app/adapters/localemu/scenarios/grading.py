"""How every scenario's check reads: a header, one `[ok]`/`[--]` line per clause, then the
verdict, so the last line is `PASS: …` or the first missed clause as `FAIL: …`."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.verifier import CheckResult


@dataclass(frozen=True, slots=True)
class Clause:
    ok: bool
    # What the line says when the clause holds, and when it does not.
    met: str
    missed: str


def verdict(header: str, clauses: list[Clause], passed: str) -> CheckResult:
    lines = [header, *(f"[ok] {c.met}" if c.ok else f"[--] {c.missed}" for c in clauses)]
    missed = next((c.missed for c in clauses if not c.ok), None)
    if missed is None:
        return CheckResult(passed=True, output="\n".join([*lines, f"PASS: {passed}"]))
    return CheckResult(passed=False, output="\n".join([*lines, f"FAIL: {missed}"]))


def gone(what: str) -> CheckResult:
    """The run's resources are gone (deleted, or the emulator restarted): ungradable."""
    return CheckResult(passed=False, unavailable_reason=f"{what} is gone; set the lab up again.")
