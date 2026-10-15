"""Pack-to-backend mapping: missing, unmapped, heavy and drifted weights, as pure data."""

from __future__ import annotations

from app.domain.verifier import VerifierQuestion
from app.domain.verifier_mapping import WeightDrift, compare_mapping


def _q(qid: str, weight: int = 4, requires: str = "") -> VerifierQuestion:
    return VerifierQuestion(
        id=qid,
        title=f"Stub {qid}",
        weight=weight,
        context="",
        description="",
        hint="",
        requires=requires,
    )


def test_compare_mapping_sorts_every_difference() -> None:
    served = [_q("b", 5), _q("a", 7, requires="heavy"), _q("c")]
    report = compare_mapping("cka", ["c", "a", "zz"], served, lab_weights={"a": 7, "c": 2, "zz": 1})
    assert not report.ok
    assert report.missing_questions == ("zz",)
    assert report.unmapped_questions == ("b",)
    assert report.heavy_questions == ("a",)
    assert report.weight_drift == (WeightDrift(question="c", pack_weight=2, served_weight=4),)
    assert (report.lab_count, report.question_count) == (3, 3)


def test_compare_mapping_without_weights_reports_no_drift() -> None:
    report = compare_mapping("cka2", ["a"], [_q("a", 9)])
    assert report.ok
    assert report.weight_drift == () and report.unmapped_questions == ()
