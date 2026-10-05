from __future__ import annotations

import copy

import pytest

from app.domain.content.validate import content_hash, parse_pack, validate_pack
from app.domain.exceptions import ValidationError
from tests.fixtures import mini_pack


def _questions(pack: dict[str, object]) -> list[dict[str, object]]:
    questions = pack["questions"]
    assert isinstance(questions, list)
    return questions


def test_mini_pack_is_valid() -> None:
    spec = parse_pack(mini_pack())
    report = validate_pack(spec)
    assert report.ok, report.as_dict()


def test_unknown_key_is_a_schema_error() -> None:
    pack = mini_pack()
    _questions(pack)[0]["bogus"] = 1
    with pytest.raises(ValidationError) as exc:
        parse_pack(pack)
    assert "bogus" in str(exc.value.details)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda q: q["options"].append({"id": "o1", "text_md": "dup id"}),
        lambda q: q["options"].append({"id": "o9", "text_md": q["options"][0]["text_md"]}),
        lambda q: q.update(select_count=2),
        lambda q: q["distractor_rationales"].pop("o2"),
        lambda q: q.update(correct_option_ids=["o9"]),
        lambda q: q.update(explanation_md=""),
    ],
    ids=[
        "dup-option-id",
        "dup-option-text",
        "cardinality",
        "missing-rationale",
        "unknown-correct",
        "no-explanation",
    ],
)
def test_question_consistency_rules(mutate: object) -> None:
    pack = mini_pack()
    mutate(_questions(pack)[0])  # type: ignore[operator]
    with pytest.raises(ValidationError):
        parse_pack(pack)


def test_cross_reference_errors() -> None:
    pack = mini_pack()
    _questions(pack)[0]["objectives"] = ["9.9"]
    _questions(pack)[1]["slug"] = "q-3"
    domains = pack["domains"]
    assert isinstance(domains, list)
    domains[0]["weight_percent"] = 50
    report = validate_pack(parse_pack(pack))
    codes = {issue.code for issue in report.errors}
    assert codes == {"unknown_objective", "duplicate_key", "weights"}


def test_ai_marked_human_reviewed_is_a_warning() -> None:
    pack = mini_pack()
    _questions(pack)[0]["review_status"] = "human_reviewed"
    report = validate_pack(parse_pack(pack))
    assert report.ok and any(w.code == "provenance" for w in report.warnings)


def test_content_hash_is_stable_and_sensitive_to_content() -> None:
    spec = parse_pack(mini_pack())
    again = parse_pack(copy.deepcopy(mini_pack()))
    assert content_hash(spec.questions[0]) == content_hash(again.questions[0])
    changed = mini_pack()
    _questions(changed)[0]["stem_md"] = "different"
    assert content_hash(parse_pack(changed).questions[0]) != content_hash(spec.questions[0])


def test_verified_exam_metadata_needs_sources_and_date() -> None:
    pack = mini_pack()
    exam = pack["exam_version"]
    assert isinstance(exam, dict)
    exam["verification"] = {"status": "verified", "checked_on": None, "sources": []}
    with pytest.raises(ValidationError):
        parse_pack(pack)
