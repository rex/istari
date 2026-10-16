"""Composing one objective's learning path, and the lecture block in the daily plan."""

from __future__ import annotations

from app.domain.learning_path import PathLecture, compose_path, stale_courses
from app.domain.planning_types import LectureCandidate, PlannerInput
from app.domain.recommendation import plan_session


def _lecture(
    course: str,
    path: str,
    title: str,
    *,
    minutes: float = 10.0,
    score: float = 0.8,
    source: str = "lexical",
    currency: str = "current",
    section: str = "01",
) -> PathLecture:
    return PathLecture(
        course_slug=course,
        course_title=course.upper(),
        lecture_path=path,
        lecture_title=title,
        minutes=minutes,
        score=score,
        source=source,
        currency=currency,
        section_title=section,
    )


DEEP = [
    _lecture("deep", "02 - IAM/010 Policies.mp4", "Policies", score=0.7),
    _lecture("deep", "02 - IAM/002 Users and groups.mp4", "Users and groups", score=0.6),
    _lecture("deep", "02 - IAM/003 Roles.mp4", "Roles", score=0.9),
]
SHALLOW = [
    _lecture("shallow", "01 - Intro/001 Roles.mp4", "Roles", score=1.0),
    _lecture("shallow", "01 - Intro/002 STS deep dive.mp4", "STS deep dive", score=0.95),
]


def test_anchor_is_the_deepest_course_in_course_order_then_the_fill() -> None:
    entries = compose_path(SHALLOW + DEEP)
    assert [e.lecture_path for e in entries[:3]] == [
        "02 - IAM/002 Users and groups.mp4",
        "02 - IAM/003 Roles.mp4",
        "02 - IAM/010 Policies.mp4",
    ]
    assert "deepest coverage" in entries[0].reason and "30 min" in entries[0].reason
    # The fill skips the lecture whose title the anchor already covers ("Roles").
    assert [e.lecture_path for e in entries[3:]] == ["01 - Intro/002 STS deep dive.mp4"]
    assert "strongest match left (95%)" in entries[3].reason
    assert all(e.source == "proposed" for e in entries)


def test_pins_lead_exclusions_never_return_and_the_cap_holds() -> None:
    pinned = [("shallow", "01 - Intro/002 STS deep dive.mp4")]
    excluded = {("deep", "02 - IAM/010 Policies.mp4")}
    entries = compose_path(SHALLOW + DEEP, pinned=pinned, excluded=excluded, cap_minutes=25)
    assert (entries[0].course_slug, entries[0].lecture_path) == pinned[0]
    assert entries[0].source == "pinned" and entries[0].reason == "pinned by you"
    paths = [e.lecture_path for e in entries]
    assert "02 - IAM/010 Policies.mp4" not in paths
    # 10 min pinned + 10 + 10 from the anchor reaches the 25-minute cap; nothing more.
    assert paths[1:] == ["02 - IAM/002 Users and groups.mp4", "02 - IAM/003 Roles.mp4"]


def test_an_older_exam_course_steps_aside_when_a_current_one_covers_it() -> None:
    older = [
        _lecture("old", f"01/00{i} Old {i}.mp4", f"Old {i}", minutes=20, currency="older")
        for i in range(1, 4)
    ]
    current = [
        _lecture("new", "01/001 New 1.mp4", "New 1", minutes=20),
        _lecture("new", "01/002 New 2.mp4", "New 2", minutes=20),
    ]
    assert stale_courses(older + current) == ["OLD"]
    entries = compose_path(older + current)
    assert {e.course_slug for e in entries} == {"new"}
    # Without a current course the older one is simply the deepest.
    assert stale_courses(older) == []
    assert {e.course_slug for e in compose_path(older)} == {"old"}


def test_a_course_for_this_exam_anchors_over_a_longer_one_for_another() -> None:
    other = [
        _lecture(
            "devops", f"01/00{i} Pipelines {i}.mp4", f"Pipelines {i}", minutes=30, currency="other"
        )
        for i in range(1, 5)
    ]
    own = [
        _lecture("saa", "03 - IAM/001 IAM basics.mp4", "IAM basics", minutes=30, score=0.9),
        _lecture("saa", "03 - IAM/002 Roles.mp4", "Roles", minutes=30, score=0.9),
        _lecture("saa", "03 - IAM/003 Policies.mp4", "Policies", minutes=30, score=0.9),
    ]
    # 81 of the other course's 96 weighted minutes: the exam's own course leads.
    assert compose_path(other + own)[0].course_slug == "saa"
    # Well under half its depth, the longer course leads after all.
    assert compose_path(other + own[:1])[0].course_slug == "devops"


def test_a_course_for_this_exam_with_a_path_of_its_own_beats_a_much_longer_other() -> None:
    other = [
        _lecture("pro", f"01/0{i} Pro {i}.mp4", f"Pro {i}", minutes=60, currency="other")
        for i in range(1, 9)
    ]
    own = [
        _lecture("saa", f"02/0{i} Own {i}.mp4", f"Own {i}", minutes=40, score=0.9)
        for i in range(1, 5)
    ]
    # 160 own minutes against 480 other: under half the depth, but enough to fill two hours.
    assert compose_path(other + own)[0].course_slug == "saa"
    assert compose_path(other + own[:2])[0].course_slug == "pro"


def test_the_anchor_run_starts_at_the_most_relevant_section() -> None:
    course = [
        _lecture("c", "01 - Welcome/001 Intro.mp4", "Intro", score=0.5, section="01 - Welcome"),
        _lecture("c", "01 - Welcome/002 Setup.mp4", "Setup", score=0.5, section="01 - Welcome"),
        _lecture("c", "04 - IAM/002 Roles.mp4", "Roles", score=0.95, section="04 - IAM"),
        _lecture("c", "04 - IAM/001 Users.mp4", "Users", score=0.9, section="04 - IAM"),
    ]
    assert [e.lecture_path for e in compose_path(course)] == [
        "04 - IAM/001 Users.mp4",
        "04 - IAM/002 Roles.mp4",
        "01 - Welcome/001 Intro.mp4",
        "01 - Welcome/002 Setup.mp4",
    ]


def test_unknown_lengths_still_cost_time_against_the_cap() -> None:
    unmeasured = [_lecture("c", f"01/00{i}.mp4", f"Lecture {i}", minutes=0) for i in range(1, 30)]
    entries = compose_path(unmeasured, cap_minutes=40)
    assert len(entries) == 5 and all(e.minutes == 0 for e in entries)


def _plan_input(minutes: int, lecture: LectureCandidate | None) -> PlannerInput:
    return PlannerInput(
        minutes=minutes,
        active_session=None,
        due_reviews=0,
        reviews_remaining_today=10,
        backlog_mode="normal",
        objectives=(),
        available_questions=5,
        next_lesson=None,
        next_lecture=lecture,
    )


def test_a_thirty_minute_plan_takes_one_lecture_from_the_path() -> None:
    lecture = LectureCandidate(
        course_slug="deep",
        lecture_path="02 - IAM/003 Roles.mp4",
        title="Roles",
        course_title="DEEP",
        objective_code="1.1",
        minutes=12,
    )
    short = plan_session(_plan_input(15, lecture))
    assert all(block.kind != "lecture" for block in short.blocks)
    long = plan_session(_plan_input(30, lecture))
    block = next(block for block in long.blocks if block.kind == "lecture")
    assert block.label == "Watch: Roles" and block.focus == "objective:1.1"
    assert (block.course_slug, block.lecture_path) == ("deep", "02 - IAM/003 Roles.mp4")
    assert "about 12 min" in block.reason
