from __future__ import annotations

from app.domain.planning_types import (
    ActiveSession,
    LabCandidate,
    LessonCandidate,
    ObjectiveEvidence,
    PlannerInput,
)
from app.domain.recommendation import plan_session, weakest_objectives


def _obj(
    code: str, attempts: int, correct: int, weight: int = 30, questions: int = 10
) -> ObjectiveEvidence:
    return ObjectiveEvidence(code, f"Objective {code}", weight, attempts, correct, questions)


def _input(**overrides: object) -> PlannerInput:
    base: dict[str, object] = {
        "minutes": 15,
        "active_session": None,
        "due_reviews": 0,
        "reviews_remaining_today": 50,
        "backlog_mode": "normal",
        "objectives": (_obj("1.1", 0, 0), _obj("2.1", 0, 0)),
        "available_questions": 20,
        "next_lesson": LessonCandidate("lesson-one", "Lesson One", 5),
    }
    base.update(overrides)
    return PlannerInput(**base)  # type: ignore[arg-type]


def test_resume_wins_over_everything() -> None:
    plan = plan_session(_input(active_session=ActiveSession(7, "practice", 2, 5), due_reviews=40))
    assert [b.kind for b in plan.blocks] == ["resume"]
    assert plan.blocks[0].session_id == 7 and plan.blocks[0].count == 3


def test_no_evidence_means_mixed_practice() -> None:
    plan = plan_session(_input(minutes=5))
    assert [b.kind for b in plan.blocks] == ["practice"]
    assert plan.blocks[0].focus == "mixed" and plan.blocks[0].count == 5


def test_weak_objective_gets_focus_with_explanation() -> None:
    objectives = (_obj("1.1", 6, 2), _obj("2.1", 6, 6))
    plan = plan_session(_input(objectives=objectives))
    practice = next(b for b in plan.blocks if b.kind == "practice")
    assert practice.focus == "objective:1.1"
    assert "2/6" in practice.reason and "33%" in practice.reason


def test_weakest_tie_break_accuracy_then_evidence_then_weight_then_code() -> None:
    objectives = (
        _obj("3.1", 4, 2, weight=20),
        _obj("1.2", 4, 2, weight=30),
        _obj("1.1", 8, 4, weight=30),
        _obj("2.2", 3, 0, weight=26),
        _obj("4.1", 2, 0, weight=20),  # below MIN_EVIDENCE: never "weak"
    )
    assert [o.code for o in weakest_objectives(objectives)] == ["2.2", "1.1", "1.2", "3.1"]


def test_reviews_come_first_and_respect_daily_limit() -> None:
    plan = plan_session(_input(due_reviews=25, reviews_remaining_today=4))
    assert plan.blocks[0].kind == "review" and plan.blocks[0].count == 4
    assert "daily limit" in plan.blocks[0].reason


def test_recovery_mode_caps_reviews_at_ten() -> None:
    plan = plan_session(_input(minutes=30, due_reviews=200, backlog_mode="recovery"))
    assert plan.blocks[0].count == 10


def test_thirty_minutes_includes_a_lesson_five_does_not() -> None:
    assert any(b.kind == "lesson" for b in plan_session(_input(minutes=30)).blocks)
    assert not any(b.kind == "lesson" for b in plan_session(_input(minutes=5)).blocks)


def test_nothing_available_is_stated_plainly() -> None:
    plan = plan_session(_input(available_questions=0, next_lesson=None))
    assert plan.blocks == () and plan.headline == "Nothing scheduled"


def _lab() -> LabCandidate:
    return LabCandidate("lab-verified", "Fix the crashing pod", 10, "2.1", "Objective 2.1")


def test_verified_lab_is_scheduled_once_while_the_cluster_answers() -> None:
    plan = plan_session(_input(minutes=30, verified_lab=_lab(), lab_backend="ready"))
    kinds = [b.kind for b in plan.blocks]
    assert kinds == ["practice", "lab", "lesson"]
    lab = plan.blocks[1]
    assert lab.item_key == "lab-verified" and lab.count == 1 and "objective 2.1" in lab.reason
    assert any("the cluster grades it" in line for line in plan.explanation)


def test_verified_lab_waits_for_a_real_session_length() -> None:
    plan = plan_session(_input(minutes=5, verified_lab=_lab(), lab_backend="ready"))
    assert [b.kind for b in plan.blocks] == ["practice"]
    assert not any("lab" in line.lower() for line in plan.explanation)


def test_unreachable_cluster_skips_the_lab_and_says_so() -> None:
    plan = plan_session(_input(minutes=15, verified_lab=_lab(), lab_backend="unreachable"))
    assert [b.kind for b in plan.blocks] == ["practice"]
    assert any("not reachable" in line for line in plan.explanation)
    silent = plan_session(_input(minutes=15, verified_lab=_lab(), lab_backend="unconfigured"))
    assert not any("lab" in line.lower() for line in silent.explanation)


def test_a_lab_can_headline_when_nothing_else_is_due() -> None:
    plan = plan_session(
        _input(minutes=15, available_questions=0, verified_lab=_lab(), lab_backend="ready")
    )
    assert [b.kind for b in plan.blocks] == ["lab"] and plan.headline.startswith("Lab:")
