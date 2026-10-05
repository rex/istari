"""Content administration: listing, editing, import/export."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from app.contracts.common import ApiModel

ItemKind = Literal["lesson", "question", "flashcard", "lab"]
ItemStatus = Literal["active", "retired", "invalidated"]
ReviewStatus = Literal["draft", "source_checked", "human_reviewed"]


class ContentItemSummary(ApiModel):
    key: str
    kind: str
    family_key: str
    status: str
    user_approved: bool
    revision: int
    review_status: str
    objectives: list[str]
    preview: str
    updated_at: datetime


class ContentItemDetail(ContentItemSummary):
    pack_slug: str
    content: dict[str, object]
    sources: list[dict[str, object]]
    provenance: dict[str, object]
    revisions: list[int]


class ContentItemUpdate(ApiModel):
    """A full item body in pack-schema shape (kind-specific); creates a new revision."""

    item: dict[str, object]
    note: str = Field(default="", max_length=500)


class ContentItemFlags(ApiModel):
    status: ItemStatus | None = None
    user_approved: bool | None = None


class ContentListResponse(ApiModel):
    items: list[ContentItemSummary]
    total: int


class ImportRequest(ApiModel):
    pack: dict[str, object]
    dry_run: bool = True


class ImportReportView(ApiModel):
    pack_slug: str
    dry_run: bool
    created: list[str]
    updated: list[str]
    unchanged: list[str]
    retired: list[str]
    track_changes: list[str]
    warnings: list[dict[str, object]]
    counts: dict[str, int]
