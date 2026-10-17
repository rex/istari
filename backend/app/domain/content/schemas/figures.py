"""A figure: a drawing of the thing a lesson teaches, kept and reviewed as pack content."""

from __future__ import annotations

import re

from pydantic import model_validator

from app.domain.content.schemas.common import ItemBase, NonEmpty

# Two megabytes is a drawing with its icons inlined, not a photograph.
MAX_SVG_BYTES = 2_000_000

# What a drawing served as an image must not carry: anything that runs or reaches out.
_FORBIDDEN = (
    re.compile(r"<\s*(script|foreignObject|iframe|object|embed)\b", re.I),
    re.compile(r"<[^>]*\son[a-z]+\s*=", re.I),
    re.compile(r"href\s*=\s*[\"'](?!#|data:image/)", re.I),
    re.compile(r"url\(\s*[\"']?(?!#)", re.I),
)
_PROLOG = re.compile(r"^(?:\s|<\?xml.*?\?>|<!DOCTYPE[^>]*>|<!--.*?-->)*", re.S)
_PLACED = re.compile(r"\]\(figure:([a-z0-9][a-z0-9-]{1,98})\)")


def placed_figures(body_md: str) -> list[str]:
    """The figure slugs a lesson body places inline as `![alt](figure:slug)`, in order."""
    seen: list[str] = []
    for slug in _PLACED.findall(body_md):
        if slug not in seen:
            seen.append(slug)
    return seen


class FigureSpec(ItemBase):
    """A drawing of the thing: an SVG with the provider's own icons, rendered offline from the
    script kept beside it, committed, reviewed and served like any item, and shown in the
    lesson viewer and beside the lectures mapped to its objectives.

    `file` is where the pack keeps the drawing (relative to the pack folder); the loader reads
    it into `svg`, which is the versioned content. A pack sent over the API carries `svg`
    inline. The path never enters the content hash, so an export re-imports unchanged.
    """

    title: NonEmpty
    # The decision rule the drawing shows, in a sentence or two. Rendered as Markdown.
    caption_md: NonEmpty
    # What the drawing shows, for readers who cannot see it.
    alt: NonEmpty
    file: str | None = None
    svg: str = ""

    @model_validator(mode="after")
    def svg_is_inert(self) -> FigureSpec:
        if not self.svg:
            return self  # not loaded yet; validate_pack refuses an empty drawing
        if len(self.svg.encode("utf-8")) > MAX_SVG_BYTES:
            raise ValueError(f"{self.slug}: svg is over {MAX_SVG_BYTES} bytes")
        if not _PROLOG.sub("", self.svg, count=1).startswith("<svg"):
            raise ValueError(f"{self.slug}: svg must be an <svg> document")
        for pattern in _FORBIDDEN:
            if pattern.search(self.svg):
                raise ValueError(
                    f"{self.slug}: svg carries a script, an event handler, an embedded document "
                    "or an external reference, which a figure must not"
                )
        return self
