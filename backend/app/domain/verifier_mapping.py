"""How a pack's verified labs line up with the questions a backend serves. Pure data."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.verifier import VerifierQuestion


@dataclass(frozen=True, slots=True)
class MappingReport:
    profile: str
    missing_questions: tuple[str, ...] = ()
    unmapped_questions: tuple[str, ...] = ()
    heavy_questions: tuple[str, ...] = ()
    lab_count: int = 0
    question_count: int = 0

    @property
    def ok(self) -> bool:
        return not self.missing_questions


def questions_by_id(questions: list[VerifierQuestion]) -> dict[str, VerifierQuestion]:
    return {question.id: question for question in questions}


def compare_mapping(
    profile: str, lab_questions: list[str], served: list[VerifierQuestion]
) -> MappingReport:
    """Labs whose question id the backend does not serve, and questions no lab covers."""
    served_ids = {question.id for question in served}
    wanted = set(lab_questions)
    return MappingReport(
        profile=profile,
        missing_questions=tuple(sorted(wanted - served_ids)),
        unmapped_questions=tuple(sorted(served_ids - wanted)),
        heavy_questions=tuple(sorted(q.id for q in served if q.requires == "heavy")),
        lab_count=len(lab_questions),
        question_count=len(served),
    )
