"""What watching did: per objective, the lectures watched and the first-attempt accuracy
before and after the first of them. Correlation with small samples, shown as such."""

from __future__ import annotations

from datetime import datetime

from app.contracts.common import ApiModel


class WatchOutcome(ApiModel):
    lectures_watched: int
    first_watched_at: datetime | None
    before_attempts: int
    before_correct: int
    after_attempts: int
    after_correct: int
