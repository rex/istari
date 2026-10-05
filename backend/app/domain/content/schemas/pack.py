"""The pack root document."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from app.domain.content.schemas.common import AuthoredBy, Key, NonEmpty, StrictModel
from app.domain.content.schemas.items import FlashcardSpec, LabSpec, LessonSpec, QuestionSpec
from app.domain.content.schemas.track import (
    CertificationSpec,
    DomainSpec,
    ExamVersionSpec,
    SubjectSpec,
)

SemVer = Annotated[str, StringConstraints(pattern=r"^\d+\.\d+\.\d+$")]


class PackMeta(StrictModel):
    slug: Key
    name: NonEmpty
    version: SemVer
    description: str = ""
    authored_by: AuthoredBy
    # What is and is not covered, in the author's own words. Shown in the app.
    coverage_notes_md: str = ""


class ContentPackSpec(StrictModel):
    schema_version: Literal[1]
    pack: PackMeta
    subject: SubjectSpec
    certification: CertificationSpec
    exam_version: ExamVersionSpec
    domains: list[DomainSpec] = Field(min_length=1)
    lessons: list[LessonSpec] = Field(default_factory=list)
    questions: list[QuestionSpec] = Field(default_factory=list)
    flashcards: list[FlashcardSpec] = Field(default_factory=list)
    labs: list[LabSpec] = Field(default_factory=list)
