"""The optional `verifier` on a lab: which backend grades it, and which task it runs there.

A verified lab is still a lab brief: the owner's goals, prerequisites and cleanup notes.
The backend supplies the task text and the mechanical pass/fail; Istari stores only the
reference (backend, profile, question id), never the backend's own text. K16S serves its own
tasks; `localemu` tasks are Istari's scenarios, graded against the LocalEmu AWS emulator.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, StringConstraints, field_validator

from app.domain.content.schemas.common import NonEmpty, StrictModel

# Every backend the schema knows about. Only the implemented ones may appear in a pack; the
# others are reserved so a future pack cannot pick a name the engine will interpret differently.
VerifierBackend = Literal["k16s", "ck-x", "localemu", "real-aws", "kubernetes"]
IMPLEMENTED_BACKENDS: frozenset[str] = frozenset({"k16s", "localemu"})

QuestionId = Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9._-]{0,78}$")]


class LabVerifierSpec(StrictModel):
    backend: VerifierBackend
    # The backend's own grouping: a K16S exam profile (`cka`, `cka2`) or a LocalEmu scenario
    # family (`saa`).
    profile: NonEmpty
    # The backend's question id (a K16S question, or a LocalEmu scenario id such as
    # `s3-lifecycle`). Text is fetched live from the backend, never stored here.
    question: QuestionId
    # Relative weight, as the backend scores it (K16S questions carry 4 to 8).
    weight: int = Field(default=1, ge=1, le=20)
    time_limit_minutes: int | None = Field(default=None, ge=1, le=240)

    @field_validator("backend")
    @classmethod
    def backend_is_implemented(cls, value: str) -> str:
        if value not in IMPLEMENTED_BACKENDS:
            implemented = ", ".join(sorted(IMPLEMENTED_BACKENDS))
            raise ValueError(
                f"verifier backend '{value}' is reserved but not implemented yet; "
                f"only {implemented} can grade a lab today"
            )
        return value
