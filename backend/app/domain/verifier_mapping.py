"""How a pack's verified labs line up with the questions a backend serves. Pure data."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.verifier import VerifierQuestion


@dataclass(frozen=True, slots=True)
class WeightDrift:
    """A lab's stored weight no longer matches what the backend serves for its question."""

    question: str
    pack_weight: int
    served_weight: int


@dataclass(frozen=True, slots=True)
class MappingReport:
    profile: str
    missing_questions: tuple[str, ...] = ()
    unmapped_questions: tuple[str, ...] = ()
    heavy_questions: tuple[str, ...] = ()
    weight_drift: tuple[WeightDrift, ...] = ()
    lab_count: int = 0
    question_count: int = 0

    @property
    def ok(self) -> bool:
        return not self.missing_questions


def questions_by_id(questions: list[VerifierQuestion]) -> dict[str, VerifierQuestion]:
    return {question.id: question for question in questions}


def compare_mapping(
    profile: str,
    lab_questions: list[str],
    served: list[VerifierQuestion],
    *,
    lab_weights: dict[str, int] | None = None,
) -> MappingReport:
    """Labs whose question the backend does not serve, questions no lab covers, and weights
    that drifted since the pack was written (when the pack's weights are given)."""
    by_id = questions_by_id(served)
    wanted = set(lab_questions)
    drift = tuple(
        WeightDrift(question=qid, pack_weight=weight, served_weight=by_id[qid].weight)
        for qid, weight in sorted((lab_weights or {}).items())
        if qid in by_id and by_id[qid].weight != weight
    )
    return MappingReport(
        profile=profile,
        missing_questions=tuple(sorted(wanted - set(by_id))),
        unmapped_questions=tuple(sorted(set(by_id) - wanted)),
        heavy_questions=tuple(sorted(q.id for q in served if q.requires == "heavy")),
        weight_drift=drift,
        lab_count=len(lab_questions),
        question_count=len(served),
    )
