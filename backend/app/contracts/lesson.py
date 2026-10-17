"""Lessons, reading progress, notes."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.contracts.common import ApiModel, ObjectiveRef, SourceView
from app.contracts.figure import FigureView
from app.contracts.lab import LabSummary


class ItemProgressView(ApiModel):
    position: float
    bookmarked: bool
    completed_at: datetime | None
    last_opened_at: datetime | None


class NoteView(ApiModel):
    id: int
    item_key: str | None
    body_md: str
    created_at: datetime
    updated_at: datetime


class NoteCreate(ApiModel):
    item_key: str | None = None
    body_md: str = Field(min_length=1, max_length=8000)


class NotePatch(ApiModel):
    body_md: str = Field(min_length=1, max_length=8000)


class LessonCheckView(ApiModel):
    prompt_md: str
    answer_md: str


class LessonSummary(ApiModel):
    item_key: str
    title: str
    summary: str
    estimated_minutes: int
    objectives: list[ObjectiveRef]
    domain_code: str
    review_status: str
    authored_by: str
    progress: ItemProgressView
    self_declared_familiar: bool


class LessonView(LessonSummary):
    body_md: str
    foundations_md: str
    checks: list[LessonCheckView]
    sources: list[SourceView]
    notes: list[NoteView]
    # The figures the lesson shows, in its order: placed in the body with
    # `![alt](figure:slug)` or following it.
    figures: list[FigureView]
    # The labs of the lesson's "Do it" step, in its order.
    labs: list[LabSummary]


class LessonProgressPatch(ApiModel):
    position: float | None = Field(default=None, ge=0.0, le=1.0)
    bookmarked: bool | None = None
    completed: bool | None = None
