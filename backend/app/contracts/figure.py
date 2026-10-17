"""Figures: a drawing of the thing, shown in a lesson and beside the lectures on its topic."""

from __future__ import annotations

from app.contracts.common import ApiModel, ObjectiveRef


class FigureView(ApiModel):
    key: str
    title: str
    caption_md: str
    alt: str
    # Where the drawing itself is served (`/api/figures/<key>.svg`).
    url: str
    objectives: list[ObjectiveRef]
