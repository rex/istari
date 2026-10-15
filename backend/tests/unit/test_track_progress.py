"""The course picker's progress line: coverage in words, accuracy only once it is evidence."""

from __future__ import annotations

from app.domain.track_progress import TrackTally, coverage_fraction, progress_sentence


def test_an_untouched_track_has_not_started() -> None:
    tally = TrackTally(lessons=8, questions=40, cards=24, labs=2)
    assert not tally.started
    assert coverage_fraction(tally) == 0.0


def test_a_labs_only_track_counts_verified_labs() -> None:
    tally = TrackTally(labs=36, verified_labs=36, labs_attempted=3, labs_passed_first=2)
    assert tally.started
    assert progress_sentence(tally) == "2 of 36 labs verified"
    assert coverage_fraction(tally) == 2 / 36


def test_accuracy_appears_only_with_enough_first_attempts() -> None:
    few = TrackTally(lessons=1, lessons_completed=1, questions=40, families_seen=2)
    assert progress_sentence(few) == f"1 of 1 lesson read {chr(0xB7)} 2 of 40 questions seen"
    enough = TrackTally(questions=40, families_seen=4, first_attempts=4, first_correct=3)
    assert progress_sentence(enough) == "75% first-attempt accuracy"


def test_coverage_never_exceeds_one_and_is_none_without_items() -> None:
    assert coverage_fraction(TrackTally()) is None
    over = TrackTally(questions=2, families_seen=2, verified_labs=1, labs_passed_first=1)
    assert coverage_fraction(over) == 1.0
    assert progress_sentence(TrackTally(cards=3, lessons_completed=0, labs_attempted=1)) == (
        "Started"
    )
