from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from app.domain.exceptions import ValidationError
from app.domain.scheduling.fsrs_adapter import DEFAULT_SETTINGS, FsrsScheduler
from app.domain.scheduling.interface import (
    RATING_AGAIN,
    RATING_EASY,
    RATING_GOOD,
    STATE_LEARNING,
    STATE_REVIEW,
)

NOW = datetime(2026, 10, 5, 20, 0, tzinfo=UTC)
DETERMINISTIC = replace(DEFAULT_SETTINGS, enable_fuzzing=False)


def test_new_card_is_due_immediately_in_learning() -> None:
    card = FsrsScheduler(DETERMINISTIC).new_card(NOW)
    assert card.due == NOW and card.state == STATE_LEARNING and card.last_review is None


def test_good_then_good_graduates_and_moves_due_forward() -> None:
    scheduler = FsrsScheduler(DETERMINISTIC)
    card = scheduler.new_card(NOW)
    first = scheduler.review(card, RATING_GOOD, NOW)
    assert first.due == NOW + timedelta(minutes=10)  # second learning step
    assert first.last_review == NOW
    second = scheduler.review(first, RATING_GOOD, first.due)
    assert second.state == STATE_REVIEW
    assert second.due > first.due + timedelta(hours=12)


def test_again_schedules_sooner_than_easy() -> None:
    scheduler = FsrsScheduler(DETERMINISTIC)
    card = scheduler.new_card(NOW)
    again = scheduler.review(card, RATING_AGAIN, NOW)
    easy = scheduler.review(card, RATING_EASY, NOW)
    assert again.due < easy.due
    assert easy.state == STATE_REVIEW


def test_deterministic_without_fuzzing() -> None:
    a = FsrsScheduler(DETERMINISTIC)
    b = FsrsScheduler(DETERMINISTIC)
    card = a.new_card(NOW)
    assert a.review(card, RATING_EASY, NOW) == b.review(card, RATING_EASY, NOW)


def test_retrievability_decays_over_time() -> None:
    scheduler = FsrsScheduler(DETERMINISTIC)
    reviewed = scheduler.review(scheduler.new_card(NOW), RATING_EASY, NOW)
    soon = scheduler.retrievability(reviewed, NOW + timedelta(hours=1))
    later = scheduler.retrievability(reviewed, NOW + timedelta(days=60))
    assert 0.0 <= later < soon <= 1.0


def test_invalid_rating_and_naive_datetime_are_rejected() -> None:
    scheduler = FsrsScheduler(DETERMINISTIC)
    card = scheduler.new_card(NOW)
    with pytest.raises(ValidationError):
        scheduler.review(card, 5, NOW)
    with pytest.raises(ValueError, match="aware"):
        scheduler.new_card(datetime(2026, 1, 1))


def test_version_names_the_library() -> None:
    assert FsrsScheduler().version.startswith("py-fsrs ")
