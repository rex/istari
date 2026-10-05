"""Exam version (track) views."""

from __future__ import annotations

from datetime import date

from app.contracts.common import ApiModel, SourceView


class ObjectiveView(ApiModel):
    id: int
    code: str
    title: str
    knowledge: list[str]
    skills: list[str]


class DomainView(ApiModel):
    id: int
    code: str
    name: str
    weight_percent: int
    objectives: list[ObjectiveView]


class TrackSummary(ApiModel):
    exam_version_id: int
    code: str
    name: str
    certification: str
    provider: str
    verification_status: str
    checked_on: date | None


class TrackView(TrackSummary):
    duration_minutes: int
    scored_questions: int
    unscored_questions: int
    passing_scaled_score: int
    score_scale: tuple[int, int]
    format_notes: str
    guide_revision: str | None
    sources: list[SourceView]
    domains: list[DomainView]
