from __future__ import annotations

import copy
from pathlib import Path

import pytest

from app.domain.content.load import inline_figure_files
from app.domain.content.schemas.figures import placed_figures
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


def _labs(pack: dict[str, object]) -> list[dict[str, object]]:
    labs = pack["labs"]
    assert isinstance(labs, list)
    return labs


def _verifier(pack: dict[str, object], index: int = 1) -> dict[str, object]:
    verifier = _labs(pack)[index]["verifier"]
    assert isinstance(verifier, dict)
    return verifier


def test_lab_verifier_is_part_of_the_content_hash() -> None:
    spec = parse_pack(mini_pack())
    verified = next(lab for lab in spec.labs if lab.slug == "lab-verified")
    assert verified.verifier is not None and verified.verifier.backend == "k16s"
    assert verified.verifier.weight == 4 and verified.verifier.time_limit_minutes is None
    changed = mini_pack()
    _verifier(changed)["weight"] = 5
    changed_spec = next(lab for lab in parse_pack(changed).labs if lab.slug == "lab-verified")
    assert content_hash(changed_spec) != content_hash(verified)


@pytest.mark.parametrize("backend", ["ck-x", "real-aws", "kubernetes"])
def test_reserved_backends_are_rejected_as_not_implemented(backend: str) -> None:
    pack = mini_pack()
    _verifier(pack)["backend"] = backend
    with pytest.raises(ValidationError) as exc:
        parse_pack(pack)
    issues = exc.value.details["issues"]
    assert isinstance(issues, list)
    assert any("not implemented" in issue["msg"] and backend in issue["msg"] for issue in issues)


@pytest.mark.parametrize("backend", ["chalkboard", "localstack"])
def test_unknown_backend_is_a_schema_error(backend: str) -> None:
    # `localstack` was the reserved name until LocalEmu replaced it (rex/istari#86).
    pack = mini_pack()
    _verifier(pack)["backend"] = backend
    with pytest.raises(ValidationError):
        parse_pack(pack)


def test_manual_labs_keep_the_long_form_minimums() -> None:
    pack = mini_pack()
    _labs(pack)[0]["steps_md"] = "Set up, work, check."
    with pytest.raises(ValidationError) as exc:
        parse_pack(pack)
    assert "steps_md needs at least 200" in str(exc.value.details)
    # The same short text is fine once a verifier supplies the task.
    _labs(pack)[0]["verifier"] = {"backend": "k16s", "profile": "cka", "question": "stub-x"}
    assert parse_pack(pack).labs[0].verifier is not None


def test_verifier_question_ids_are_slugs() -> None:
    pack = mini_pack()
    _verifier(pack)["question"] = "Not A Slug"
    with pytest.raises(ValidationError):
        parse_pack(pack)


def _figure(pack: dict[str, object]) -> dict[str, object]:
    figures = pack["figures"]
    assert isinstance(figures, list)
    return figures[0]


@pytest.mark.parametrize(
    "svg",
    [
        '<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg"><rect onload="alert(1)"/></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg"><a xlink:href="https://evil.test/">x</a></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg"><foreignObject>x</foreignObject></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg"><rect style="fill:url(https://e.test/x)"/></svg>',
        "<div>not a drawing</div>",
    ],
    ids=["script", "handler", "external-link", "foreign-object", "external-url", "not-svg"],
)
def test_a_figure_drawing_must_be_inert_svg(svg: str) -> None:
    pack = mini_pack()
    _figure(pack)["svg"] = svg
    with pytest.raises(ValidationError):
        parse_pack(pack)


def test_graphviz_output_with_inlined_icons_is_accepted() -> None:
    pack = mini_pack()
    _figure(pack)["svg"] = (
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'
        '<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" '
        '"http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">\n'
        "<!-- Generated by graphviz version 14.0.0 -->\n"
        '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">'
        '<image xlink:href="data:image/png;base64,iVBORw0KGgo=" width="1" height="1"/>'
        '<a xlink:href="#top">t</a></svg>'
    )
    assert parse_pack(pack).figures[0].title == "Figure one"


def test_a_lesson_may_only_show_figures_its_pack_ships() -> None:
    pack = mini_pack()
    lessons = pack["lessons"]
    assert isinstance(lessons, list)
    lessons[1]["figures"] = ["fig-missing"]
    lessons[1]["body_md"] = str(lessons[1]["body_md"]) + "\n\n![x](figure:fig-also-missing)"
    report = validate_pack(parse_pack(pack))
    assert [(issue.code, issue.item_key) for issue in report.errors] == [
        ("unknown_figure", "lesson-two"),
        ("unknown_figure", "lesson-two"),
    ]


def test_a_lesson_may_only_use_labs_its_pack_ships() -> None:
    pack = mini_pack()
    lessons = pack["lessons"]
    assert isinstance(lessons, list)
    lessons[0]["labs"] = ["lab-verified", "lab-missing"]
    report = validate_pack(parse_pack(pack))
    assert [(issue.code, issue.item_key) for issue in report.errors] == [
        ("unknown_lab", "lesson-one")
    ]


def test_an_unloaded_drawing_is_an_error_not_a_crash() -> None:
    pack = mini_pack()
    _figure(pack).update(svg="", file="figures/one.svg")
    report = validate_pack(parse_pack(pack))
    assert [issue.code for issue in report.errors] == ["empty_figure"]


def test_the_drawing_file_is_read_from_the_pack_folder_and_stays_out_of_the_hash(
    tmp_path: Path,
) -> None:
    pack = mini_pack()
    drawing = str(_figure(pack)["svg"])
    (tmp_path / "figures").mkdir()
    (tmp_path / "figures" / "one.svg").write_text(drawing, encoding="utf-8")
    from_file = copy.deepcopy(pack)
    _figure(from_file).update(svg="", file="figures/one.svg")
    loaded = parse_pack(inline_figure_files(from_file, tmp_path))
    assert loaded.figures[0].svg == drawing
    assert content_hash(loaded.figures[0]) == content_hash(parse_pack(pack).figures[0])

    outside = copy.deepcopy(pack)
    _figure(outside).update(svg="", file="../one.svg")
    with pytest.raises(ValidationError):
        inline_figure_files(outside, tmp_path)


def test_placed_figures_reads_the_body_in_order_once_each() -> None:
    body = "![a](figure:one) text ![b](figure:two) ![c](figure:one) ![d](https://x.test/i.png)"
    assert placed_figures(body) == ["one", "two"]
