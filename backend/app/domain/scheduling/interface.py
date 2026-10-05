"""Scheduler interface: the only surface the rest of the app talks to.

Ratings are the four FSRS buttons. Quiz confidence is a different signal and
is never mapped onto these ratings.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

RATING_AGAIN = 1
RATING_HARD = 2
RATING_GOOD = 3
RATING_EASY = 4
RATINGS = (RATING_AGAIN, RATING_HARD, RATING_GOOD, RATING_EASY)

STATE_LEARNING = 1
STATE_REVIEW = 2
STATE_RELEARNING = 3


@dataclass(frozen=True, slots=True)
class CardState:
    """Scheduler-visible state of one card. Times are aware UTC datetimes."""

    state: int
    step: int | None
    stability: float | None
    difficulty: float | None
    due: datetime
    last_review: datetime | None


@dataclass(frozen=True, slots=True)
class SchedulerSettings:
    """Frozen configuration; persisted as a `scheduler_configs` row."""

    name: str
    parameters: tuple[float, ...]
    desired_retention: float
    learning_steps_seconds: tuple[int, ...]
    relearning_steps_seconds: tuple[int, ...]
    maximum_interval: int
    enable_fuzzing: bool


class Scheduler(Protocol):
    @property
    def version(self) -> str:
        """Library + version string stored with every event."""

    @property
    def settings(self) -> SchedulerSettings: ...

    def new_card(self, now: datetime) -> CardState: ...

    def review(
        self, card: CardState, rating: int, now: datetime, duration_ms: int | None = None
    ) -> CardState: ...

    def retrievability(self, card: CardState, now: datetime) -> float: ...
