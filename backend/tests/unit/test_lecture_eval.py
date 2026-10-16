"""The ranking levers (floor, generic terms, query weights) and the evaluation's arithmetic."""

from __future__ import annotations

import json
from pathlib import Path

from app.domain.lecture_index import Index, objective_query, query_mass, rank_lecture, specificity
from app.domain.lecture_rules import is_housekeeping
from app.domain.lecture_text import document
from app.services.lecture_eval import EvalReport, Params, Verdict, load_sample

IAM = document("iam", "IAM users roles and policies grant least privilege; roles use STS " * 3)
STORAGE = document(
    "storage", "S3 buckets and storage classes; EBS volumes and EFS file systems " * 3
)
INTRO = document("intro", "welcome to the course, in this course we cover services and the exam")
QUERIES = [
    objective_query(
        "1.1", "1", "IAM roles and least privilege", ["IAM users roles policies"], [], [], []
    ),
    objective_query("2.1", "2", "S3 buckets EBS volumes EFS", ["storage classes"], [], [], []),
]


def test_a_floor_against_the_corpus_leaves_a_lecture_about_nothing_unmapped() -> None:
    index = Index([IAM, STORAGE, INTRO])
    spec = specificity(QUERIES)
    ceilings = {
        q.code: max(index.score(doc, q, spec)[0] for doc in (IAM, STORAGE, INTRO)) for q in QUERIES
    }
    without = rank_lecture(index, INTRO, QUERIES, spec)
    with_floor = rank_lecture(index, INTRO, QUERIES, spec, ceilings=ceilings, floor=0.3)
    assert [
        s.code for s in rank_lecture(index, IAM, QUERIES, spec, ceilings=ceilings, floor=0.3)
    ] == ["1.1"]
    assert len(with_floor) <= len(without)
    assert with_floor == []


def test_generic_terms_are_those_in_most_lectures_and_are_skipped() -> None:
    docs = [
        document(str(i), "course exam service " + ("iam role " if i % 2 else "s3 bucket "))
        for i in range(24)
    ]
    index = Index(docs)
    generic = index.generic(0.8)
    assert {"course", "exam", "service"} <= generic and "iam" not in generic
    query = objective_query("x", "1", "course exam iam role", [], [], [], [])
    scored_all, _ = index.score(docs[1], query, {})
    scored_some, matched_some = index.score(docs[1], query, {}, skip=generic)
    assert scored_some < scored_all and {t for t, _ in matched_some} == {"iam", "role"}


def test_query_weights_for_bodies_and_stems_can_be_turned_down() -> None:
    full = objective_query(
        "1.1", "1", "IAM", [], [], ["policy document body"], ["a stem about roles"]
    )
    quiet = objective_query(
        "1.1",
        "1",
        "IAM",
        [],
        [],
        ["policy document body"],
        ["a stem about roles"],
        body_weight=0.0,
        stem_weight=0.5,
    )
    assert "policy" in full.weights and "policy" not in quiet.weights
    assert quiet.weights["stem"] == 0.5 and full.weights["stem"] == 1.0


def test_report_rates_and_misses(tmp_path: Path) -> None:
    report = EvalReport(
        params=Params(floor=0.2),
        verdicts=[
            Verdict("right", ("1.1",), ("1.1", "1.2")),
            Verdict("second", ("2.1",), ("1.1", "2.1")),
            Verdict("wrong", ("3.1",), ("1.1",)),
            Verdict("intro", (), ()),
            Verdict("noisy intro", (), ("1.1",)),
        ],
    )
    lines = report.lines()
    assert lines[1] == "labelled 3: top-1 33% (1), any of top-3 67% (2)"
    assert lines[2] == "no objective 2: left unmapped 50% (1)"
    assert any(line.startswith("  miss  second") for line in lines)
    assert any(line.startswith("  noise noisy intro") for line in lines)

    sample = tmp_path / "sample.json"
    sample.write_text(
        json.dumps(
            {"lectures": [{"course_slug": "c", "lecture_path": "01/a.mp4", "objectives": ["1.1"]}]}
        )
    )
    loaded = load_sample(sample)
    assert loaded[0].objectives == ("1.1",) and loaded[0].title == "01/a.mp4"


def test_housekeeping_is_a_welcome_or_a_tour_but_a_section_opening_only_up_front() -> None:
    assert is_housekeeping("Welcome and How to Use this Course")
    assert is_housekeeping("Connect with Neal & Support")
    assert is_housekeeping("Course Introduction - AWS Certified Solutions Architect Associate")
    assert is_housekeeping("1. Introduction and How to use this Course", first_section=True)
    assert is_housekeeping("Introduction", first_section=True)
    assert not is_housekeeping("Introduction")
    assert not is_housekeeping(["9. Containers", "1. Introduction"][1])
    assert not is_housekeeping("Amazon EMR Walkthrough", first_section=True)
    assert not is_housekeeping("VPC Endpoints Overview")


def test_dividing_by_query_mass_takes_the_edge_off_a_big_query() -> None:
    small = objective_query("s", "1", "IAM roles policies", [], [], [], [])
    big = objective_query(
        "b",
        "2",
        "IAM roles policies",
        ["IAM users roles policies privilege STS credentials temporary"],
        [],
        [],
        [],
    )
    spec: dict[str, float] = {}
    index = Index([IAM, STORAGE])
    raw = rank_lecture(index, IAM, [small, big], spec)
    assert raw[0].code == "b"
    mass = {q.code: query_mass(q, spec) for q in (small, big)}
    assert mass["b"] > mass["s"]
    levelled = rank_lecture(index, IAM, [small, big], spec, mass=mass, mass_power=1.0)
    assert levelled[0].code == "s"
