"""What a track card says about progress: coverage, stated as such, never a readiness score."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.recommendation import MIN_EVIDENCE

SEPARATOR = f" {chr(0xB7)} "


@dataclass(frozen=True, slots=True)
class TrackTally:
    """A track's active items by kind and what the learner has done with them."""

    lessons: int = 0
    lessons_completed: int = 0
    questions: int = 0
    families_seen: int = 0
    first_attempts: int = 0
    first_correct: int = 0
    cards: int = 0
    labs: int = 0
    verified_labs: int = 0
    labs_attempted: int = 0
    labs_passed_first: int = 0

    @property
    def started(self) -> bool:
        return bool(self.lessons_completed or self.families_seen or self.labs_attempted)


def coverage_fraction(tally: TrackTally) -> float | None:
    """Items touched over items in the pack: lessons read, question families seen, labs
    verified on the first graded attempt. None when the pack has nothing to touch."""
    denominator = tally.lessons + tally.questions + tally.verified_labs
    if denominator == 0:
        return None
    done = tally.lessons_completed + tally.families_seen + tally.labs_passed_first
    return min(1.0, done / denominator)


def _counted(done: int, total: int, noun: str, verb: str) -> str:
    unit = noun if total == 1 else f"{noun}s"
    return f"{done} of {total} {unit} {verb}"


def progress_sentence(tally: TrackTally) -> str:
    """One line in the picker's voice: counts with their units, accuracy only once it is
    evidence (the same threshold Progress uses to rate an objective)."""
    parts: list[str] = []
    if tally.lessons:
        parts.append(_counted(tally.lessons_completed, tally.lessons, "lesson", "read"))
    if tally.first_attempts >= MIN_EVIDENCE:
        pct = round(100 * tally.first_correct / tally.first_attempts)
        parts.append(f"{pct}% first-attempt accuracy")
    elif tally.questions and tally.families_seen:
        parts.append(_counted(tally.families_seen, tally.questions, "question", "seen"))
    if tally.verified_labs:
        parts.append(_counted(tally.labs_passed_first, tally.verified_labs, "lab", "verified"))
    return SEPARATOR.join(parts) or "Started"
