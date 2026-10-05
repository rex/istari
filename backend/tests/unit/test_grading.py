from __future__ import annotations

import pytest

from app.domain.exceptions import ValidationError
from app.domain.grading import grade, normalize_selection, shuffle_option_ids, validate_cardinality

OPTIONS = ["o1", "o2", "o3", "o4", "o5"]


def test_single_answer_exact_match() -> None:
    result = grade(("o2",), ["o2"])
    assert result.is_correct
    assert result.missed_option_ids == () and result.extra_option_ids == ()


def test_single_answer_wrong_reports_missed_and_extra() -> None:
    result = grade(("o3",), ["o2"])
    assert not result.is_correct
    assert result.missed_option_ids == ("o2",)
    assert result.extra_option_ids == ("o3",)


@pytest.mark.parametrize(
    ("selected", "expected"),
    [
        (("o1", "o3"), True),
        (("o3", "o1"), True),  # order never matters
        (("o1",), False),  # partial set is wrong (exact-set scoring)
        (("o1", "o3", "o4"), False),
        (("o2", "o4"), False),
    ],
)
def test_multiple_answer_exact_set(selected: tuple[str, ...], expected: bool) -> None:
    assert grade(selected, ["o1", "o3"]).is_correct is expected


def test_normalize_dedupes_and_rejects_unknown_ids() -> None:
    assert normalize_selection(["o2", "o2", "o1"], OPTIONS) == ("o2", "o1")
    with pytest.raises(ValidationError):
        normalize_selection(["o9"], OPTIONS)


def test_cardinality_enforced() -> None:
    validate_cardinality(("o1", "o2"), 2)
    with pytest.raises(ValidationError):
        validate_cardinality(("o1",), 2)
    with pytest.raises(ValidationError):
        validate_cardinality(("o1", "o2"), 1)


def test_shuffle_is_deterministic_and_a_permutation() -> None:
    first = shuffle_option_ids(OPTIONS, seed=42)
    second = shuffle_option_ids(OPTIONS, seed=42)
    assert first == second
    assert sorted(first) == sorted(OPTIONS)
    assert any(shuffle_option_ids(OPTIONS, seed=s) != OPTIONS for s in range(10))
