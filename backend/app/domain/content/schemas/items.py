"""Lesson, question, flashcard and lab item specs."""

from __future__ import annotations

import re
from typing import Annotated

from pydantic import Field, StringConstraints, model_validator

from app.domain.content.schemas.common import Difficulty, ItemBase, NonEmpty, StrictModel

# Stable, descriptive slugs (never positional letters): options are shuffled per session.
OptionId = Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9-]{0,31}$")]

MIN_DISTRACTORS = 2
MAX_OPTIONS = 6


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


class LessonCheck(StrictModel):
    """A short self-check: prompt, then a revealable answer. Not graded."""

    prompt_md: NonEmpty
    answer_md: NonEmpty


class LessonSpec(ItemBase):
    title: NonEmpty
    summary: NonEmpty
    body_md: Annotated[str, StringConstraints(min_length=200)]
    # Shown on demand for readers who want the groundwork first.
    foundations_md: str = ""
    estimated_minutes: int = Field(default=5, ge=1, le=60)
    checks: list[LessonCheck] = Field(default_factory=list)


class OptionSpec(StrictModel):
    id: OptionId
    text_md: NonEmpty


class QuestionSpec(ItemBase):
    # Family groups revisions/variants of the same scenario. Defaults to `key`.
    family: str | None = None
    difficulty: Difficulty = "medium"
    stem_md: NonEmpty
    select_count: int = Field(default=1, ge=1)
    options: list[OptionSpec] = Field(min_length=3, max_length=MAX_OPTIONS)
    correct_option_ids: list[OptionId] = Field(min_length=1)
    explanation_md: NonEmpty
    # Why each wrong option is wrong, keyed by option id. Required for every distractor.
    distractor_rationales: dict[OptionId, NonEmpty]
    # The single requirement that decides the answer (e.g. "RPO under one minute").
    decisive_constraint: NonEmpty

    @model_validator(mode="after")
    def options_are_consistent(self) -> QuestionSpec:
        ids = [o.id for o in self.options]
        if len(set(ids)) != len(ids):
            raise ValueError(f"{self.slug}: duplicate option ids")
        texts = [_normalise(o.text_md) for o in self.options]
        if len(set(texts)) != len(texts):
            raise ValueError(f"{self.slug}: duplicate option texts")
        correct = set(self.correct_option_ids)
        if len(correct) != len(self.correct_option_ids):
            raise ValueError(f"{self.slug}: duplicate correct option ids")
        if not correct <= set(ids):
            raise ValueError(f"{self.slug}: correct_option_ids reference unknown options")
        if len(correct) != self.select_count:
            raise ValueError(
                f"{self.slug}: select_count ({self.select_count}) must equal the number "
                f"of correct options ({len(correct)})"
            )
        if len(ids) < self.select_count + MIN_DISTRACTORS:
            raise ValueError(f"{self.slug}: need at least {MIN_DISTRACTORS} distractors")
        distractors = set(ids) - correct
        if set(self.distractor_rationales) != distractors:
            raise ValueError(
                f"{self.slug}: distractor_rationales must cover exactly the incorrect options"
            )
        return self

    @property
    def family_key(self) -> str:
        return self.family or self.slug


class FlashcardSpec(ItemBase):
    front_md: NonEmpty
    back_md: NonEmpty
    hint_md: str = ""


class LabSpec(ItemBase):
    """A guided brief for manual, hands-on practice. Istari never provisions anything."""

    title: NonEmpty
    estimated_minutes: int = Field(ge=5, le=480)
    goals_md: NonEmpty
    prerequisites_md: NonEmpty
    cost_warning_md: Annotated[str, StringConstraints(min_length=40)]
    steps_md: Annotated[str, StringConstraints(min_length=200)]
    expected_observations_md: NonEmpty
    cleanup_md: Annotated[str, StringConstraints(min_length=40)]
