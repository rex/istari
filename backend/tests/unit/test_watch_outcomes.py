"""Splitting first attempts at the first watched lecture."""

from __future__ import annotations

from datetime import UTC, datetime

from app.services.watch_outcomes import Watched, bucket_answers


def _at(day: int) -> datetime:
    return datetime(2026, 10, day, 12, 0, tzinfo=UTC)


def test_answers_split_at_the_first_watch_and_all_count_as_before_without_one() -> None:
    watched = Watched()
    watched.add(("c", "02 - IAM/003 Roles.mp4"), _at(10))
    watched.add(("c", "02 - IAM/001 Users.mp4"), _at(8))
    watched.add(("c", "02 - IAM/001 Users.mp4"), _at(9))  # the same lecture twice counts once
    answers = [(_at(5), False), (_at(7), True), (_at(8), True), (_at(12), True), (_at(13), False)]
    outcome = bucket_answers(watched, answers)
    assert (outcome.lectures_watched, outcome.first_watched_at) == (2, _at(8))
    assert (outcome.before_attempts, outcome.before_correct) == (2, 1)
    assert (outcome.after_attempts, outcome.after_correct) == (3, 2)

    nothing = bucket_answers(Watched(), answers)
    assert nothing.lectures_watched == 0 and nothing.first_watched_at is None
    assert (nothing.before_attempts, nothing.after_attempts) == (5, 0)
