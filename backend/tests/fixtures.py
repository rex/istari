"""A small, deterministic content pack for tests (not the shipped SAA-C03 pack)."""

from __future__ import annotations

import copy
from datetime import date

CHECKED = date(2026, 10, 5).isoformat()
SOURCE = {"title": "Example source", "url": "https://docs.example.com/page", "checked_on": CHECKED}
PROVENANCE = {
    "authored_by": "ai",
    "author": "test-suite",
    "authored_on": CHECKED,
    "source_checked": True,
}


def _question(
    key: str,
    objective: str,
    correct: list[str],
    *,
    options: int = 4,
    difficulty: str = "medium",
) -> dict[str, object]:
    option_ids = [f"o{i}" for i in range(1, options + 1)]
    return {
        "slug": key,
        "objectives": [objective],
        "sources": [SOURCE],
        "provenance": PROVENANCE,
        "review_status": "source_checked",
        "difficulty": difficulty,
        "stem_md": f"Scenario for {key}: which option satisfies the constraint?",
        "select_count": len(correct),
        "options": [{"id": oid, "text_md": f"Option {oid} for {key}"} for oid in option_ids],
        "correct_option_ids": correct,
        "explanation_md": f"{correct} is correct because of the decisive constraint.",
        "distractor_rationales": {
            oid: f"{oid} ignores the constraint." for oid in option_ids if oid not in correct
        },
        "decisive_constraint": "The constraint that decides it.",
    }


def mini_pack() -> dict[str, object]:
    lesson_body = ("## Heading\n\n" + ("Lesson body text that is long enough. " * 12)).strip()
    lab_steps = ("1. Step one.\n2. Step two.\n" * 20).strip()
    return {
        "schema_version": 1,
        "pack": {
            "slug": "mini-test-pack",
            "name": "Mini test pack",
            "version": "1.0.0",
            "description": "Fixture pack for the test suite.",
            "authored_by": "ai",
            "coverage_notes_md": "Covers nothing real.",
        },
        "subject": {"slug": "testing", "name": "Testing"},
        "certification": {"slug": "test-cert", "name": "Test Certification", "provider": "Example"},
        "exam_version": {
            "code": "TST-C01",
            "name": "Test Certification v1",
            "guide_revision": "1.0",
            "duration_minutes": 60,
            "scored_questions": 10,
            "unscored_questions": 2,
            "passing_scaled_score": 700,
            "score_scale": [100, 1000],
            "format_notes": "Fixture.",
            "verification": {"status": "unverified", "checked_on": None, "sources": []},
        },
        "domains": [
            {
                "code": "1",
                "name": "Domain One",
                "weight_percent": 60,
                "objectives": [
                    {"code": "1.1", "title": "Objective 1.1", "knowledge": ["k"], "skills": ["s"]},
                    {"code": "1.2", "title": "Objective 1.2", "knowledge": [], "skills": []},
                ],
            },
            {
                "code": "2",
                "name": "Domain Two",
                "weight_percent": 40,
                "objectives": [
                    {"code": "2.1", "title": "Objective 2.1", "knowledge": [], "skills": []}
                ],
            },
        ],
        "lessons": [
            {
                "slug": "lesson-one",
                "objectives": ["1.1"],
                "sources": [SOURCE],
                "provenance": PROVENANCE,
                "review_status": "source_checked",
                "title": "Lesson One",
                "summary": "First lesson.",
                "body_md": lesson_body,
                "estimated_minutes": 4,
                "checks": [{"prompt_md": "Why?", "answer_md": "Because."}],
            },
            {
                "slug": "lesson-two",
                "objectives": ["2.1"],
                "sources": [SOURCE],
                "provenance": PROVENANCE,
                "review_status": "source_checked",
                "title": "Lesson Two",
                "summary": "Second lesson.",
                "body_md": lesson_body,
                "estimated_minutes": 6,
            },
        ],
        "questions": [
            _question("q-1", "1.1", ["o1"]),
            _question("q-2", "1.1", ["o2"]),
            _question("q-3", "1.1", ["o3"]),
            _question("q-4", "1.2", ["o4"]),
            _question("q-5", "1.2", ["o1", "o3"], options=5),
            _question("q-6", "2.1", ["o2"]),
            _question("q-7", "2.1", ["o2", "o4"], options=5),
            _question("q-8", "2.1", ["o1"], difficulty="hard"),
        ],
        "flashcards": [
            {
                "slug": f"fc-{i}",
                "objectives": ["1.1" if i < 3 else "2.1"],
                "sources": [SOURCE],
                "provenance": PROVENANCE,
                "review_status": "source_checked",
                "front_md": f"Front {i}",
                "back_md": f"Back {i}",
            }
            for i in range(1, 4)
        ],
        "labs": [
            {
                "slug": "lab-one",
                "objectives": ["1.2"],
                "sources": [SOURCE],
                "provenance": PROVENANCE,
                "review_status": "source_checked",
                "title": "Lab One",
                "estimated_minutes": 30,
                "goals_md": "Learn by doing.",
                "prerequisites_md": "An account you are allowed to use.",
                "cost_warning_md": "This lab can incur charges; nothing here is free by default.",
                "steps_md": lab_steps,
                "expected_observations_md": "You observe the thing.",
                "cleanup_md": "Delete everything you created, then confirm nothing is left behind.",
            }
        ],
    }


def pack_with_changed_question() -> dict[str, object]:
    """Same pack, q-1's stem edited (new revision expected) and q-8 removed (retire expected)."""
    pack = copy.deepcopy(mini_pack())
    questions = pack["questions"]
    assert isinstance(questions, list)
    questions[0]["stem_md"] = "Scenario for q-1, reworded: which option satisfies the constraint?"
    pack["questions"] = [q for q in questions if q["slug"] != "q-8"]
    return pack
