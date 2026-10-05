"""Subject / certification / exam version / domain / objective specs."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import Field, model_validator

from app.domain.content.schemas.common import (
    DomainCode,
    Key,
    NonEmpty,
    ObjectiveCode,
    SourceRef,
    StrictModel,
)


class SubjectSpec(StrictModel):
    slug: Key
    name: NonEmpty


class CertificationSpec(StrictModel):
    slug: Key
    name: NonEmpty
    provider: NonEmpty


class VerificationSpec(StrictModel):
    """How the exam metadata was verified. `unverified` is an honest default."""

    status: Literal["verified", "unverified"] = "unverified"
    checked_on: date | None = None
    sources: list[SourceRef] = Field(default_factory=list)
    notes: str = ""

    @model_validator(mode="after")
    def verified_needs_evidence(self) -> VerificationSpec:
        if self.status == "verified" and (self.checked_on is None or not self.sources):
            raise ValueError("status 'verified' requires checked_on and at least one source")
        return self


class ExamVersionSpec(StrictModel):
    code: NonEmpty
    name: NonEmpty
    guide_revision: str | None = None
    duration_minutes: int = Field(gt=0)
    scored_questions: int = Field(ge=0)
    unscored_questions: int = Field(ge=0)
    passing_scaled_score: int = Field(ge=0)
    score_scale: tuple[int, int]
    format_notes: str = ""
    verification: VerificationSpec = Field(default_factory=VerificationSpec)

    @model_validator(mode="after")
    def scale_is_ordered(self) -> ExamVersionSpec:
        low, high = self.score_scale
        if low >= high:
            raise ValueError("score_scale must be (min, max) with min < max")
        if not low <= self.passing_scaled_score <= high:
            raise ValueError("passing_scaled_score must lie within score_scale")
        return self


class ObjectiveSpec(StrictModel):
    code: ObjectiveCode
    title: NonEmpty
    knowledge: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)


class DomainSpec(StrictModel):
    code: DomainCode
    name: NonEmpty
    weight_percent: int = Field(ge=1, le=100)
    objectives: list[ObjectiveSpec] = Field(min_length=1)

    @model_validator(mode="after")
    def objectives_belong_to_domain(self) -> DomainSpec:
        codes = [o.code for o in self.objectives]
        if len(set(codes)) != len(codes):
            raise ValueError(f"domain {self.code}: duplicate objective codes")
        for code in codes:
            if not code.startswith(f"{self.code}."):
                raise ValueError(f"objective {code} does not belong to domain {self.code}")
        return self
