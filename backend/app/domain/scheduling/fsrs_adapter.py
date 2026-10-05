"""py-fsrs (open-spaced-repetition) behind the Scheduler interface.

API verified against the installed package (fsrs 6.3.2, 2026-10-05):
`Scheduler(parameters, desired_retention, learning_steps, relearning_steps,
maximum_interval, enable_fuzzing)`, `review_card(card, rating, review_datetime,
review_duration) -> (Card, ReviewLog)`, `get_card_retrievability(card,
current_datetime)`. Nothing here invents a memory model.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from importlib import metadata

import fsrs

from app.domain.clock import ensure_utc
from app.domain.exceptions import ValidationError
from app.domain.scheduling.interface import RATINGS, CardState, SchedulerSettings

# py-fsrs' published FSRS-6 default weights (library defaults, not ours).
DEFAULT_SETTINGS = SchedulerSettings(
    name="fsrs6-default",
    parameters=tuple(fsrs.Scheduler().parameters),
    desired_retention=0.9,
    learning_steps_seconds=(60, 600),
    relearning_steps_seconds=(600,),
    maximum_interval=36500,
    enable_fuzzing=True,
)


def library_version() -> str:
    return f"py-fsrs {metadata.version('fsrs')}"


class FsrsScheduler:
    def __init__(self, settings: SchedulerSettings = DEFAULT_SETTINGS) -> None:
        self._settings = settings
        self._impl = fsrs.Scheduler(
            parameters=list(settings.parameters),
            desired_retention=settings.desired_retention,
            learning_steps=[timedelta(seconds=s) for s in settings.learning_steps_seconds],
            relearning_steps=[timedelta(seconds=s) for s in settings.relearning_steps_seconds],
            maximum_interval=settings.maximum_interval,
            enable_fuzzing=settings.enable_fuzzing,
        )

    @property
    def version(self) -> str:
        return library_version()

    @property
    def settings(self) -> SchedulerSettings:
        return self._settings

    def new_card(self, now: datetime) -> CardState:
        return _to_state(fsrs.Card(due=ensure_utc(now)))

    def review(
        self, card: CardState, rating: int, now: datetime, duration_ms: int | None = None
    ) -> CardState:
        if rating not in RATINGS:
            raise ValidationError("rating must be 1 (Again), 2 (Hard), 3 (Good) or 4 (Easy)")
        updated, _log = self._impl.review_card(
            _from_state(card),
            fsrs.Rating(rating),
            review_datetime=ensure_utc(now),
            review_duration=duration_ms,
        )
        return _to_state(updated)

    def retrievability(self, card: CardState, now: datetime) -> float:
        return float(
            self._impl.get_card_retrievability(_from_state(card), current_datetime=ensure_utc(now))
        )


def _to_state(card: fsrs.Card) -> CardState:
    return CardState(
        state=int(card.state),
        step=card.step,
        stability=card.stability,
        difficulty=card.difficulty,
        due=ensure_utc(card.due),
        last_review=ensure_utc(card.last_review) if card.last_review else None,
    )


def _from_state(state: CardState) -> fsrs.Card:
    return fsrs.Card(
        state=fsrs.State(state.state),
        step=state.step,
        stability=state.stability,
        difficulty=state.difficulty,
        due=state.due,
        last_review=state.last_review,
    )
