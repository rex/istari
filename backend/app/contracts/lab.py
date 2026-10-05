"""Lab briefs and the evidence the user records while doing them by hand."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.contracts.common import ApiModel, ObjectiveRef, SourceView


class EvidenceView(ApiModel):
    id: int
    body_md: str
    created_at: datetime
    updated_at: datetime


class EvidenceCreate(ApiModel):
    body_md: str = Field(min_length=1, max_length=16000)


class LabSummary(ApiModel):
    item_key: str
    title: str
    estimated_minutes: int
    objectives: list[ObjectiveRef]
    evidence_count: int
    review_status: str


class LabView(LabSummary):
    goals_md: str
    prerequisites_md: str
    cost_warning_md: str
    steps_md: str
    expected_observations_md: str
    cleanup_md: str
    sources: list[SourceView]
    evidence: list[EvidenceView]
