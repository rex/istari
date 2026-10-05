"""Answer grading and option ordering. Pure functions over stable option ids.

Scoring policy (documented in docs/content-schema.md):
- Single-answer questions: exactly one option must be selected.
- Multiple-answer questions: exactly `select_count` options must be selected
  and the selected set must equal the correct set (exact-set scoring, no
  partial credit).
- Grading uses option ids. Displayed positions are never part of the key.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from app.domain.exceptions import ValidationError


@dataclass(frozen=True, slots=True)
class GradeResult:
    is_correct: bool
    selected_option_ids: tuple[str, ...]
    correct_option_ids: tuple[str, ...]
    missed_option_ids: tuple[str, ...]
    extra_option_ids: tuple[str, ...]


def normalize_selection(selected: list[str], option_ids: list[str]) -> tuple[str, ...]:
    """Dedupe while keeping order; reject ids that are not options of this question."""
    seen: list[str] = []
    allowed = set(option_ids)
    for option_id in selected:
        if option_id not in allowed:
            raise ValidationError(
                "selection contains an unknown option id", details={"option_id": option_id}
            )
        if option_id not in seen:
            seen.append(option_id)
    return tuple(seen)


def validate_cardinality(selected: tuple[str, ...], select_count: int) -> None:
    if len(selected) != select_count:
        raise ValidationError(
            f"select exactly {select_count} option(s)",
            details={"expected": select_count, "received": len(selected)},
        )


def grade(selected: tuple[str, ...], correct_option_ids: list[str]) -> GradeResult:
    """Exact-set grading."""
    selected_set = set(selected)
    correct_set = set(correct_option_ids)
    return GradeResult(
        is_correct=selected_set == correct_set,
        selected_option_ids=selected,
        correct_option_ids=tuple(correct_option_ids),
        missed_option_ids=tuple(o for o in correct_option_ids if o not in selected_set),
        extra_option_ids=tuple(o for o in selected if o not in correct_set),
    )


def shuffle_option_ids(option_ids: list[str], seed: int) -> list[str]:
    """Deterministic shuffle so a session item's order is reproducible from its seed."""
    order = list(option_ids)
    random.Random(seed).shuffle(order)  # noqa: S311 - not security sensitive
    return order
