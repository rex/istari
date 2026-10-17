"""Load a pack from disk: the JSON plus the files it points at (figure drawings)."""

from __future__ import annotations

import json
from pathlib import Path

from app.domain.content.schemas.pack import ContentPackSpec
from app.domain.content.validate import parse_pack
from app.domain.exceptions import ValidationError


def inline_figure_files(data: object, base_dir: Path) -> object:
    """Read each figure's `file` (relative to the pack folder) into its `svg`. A figure that
    already carries `svg` keeps it. A path may not leave the pack folder."""
    if not isinstance(data, dict):
        return data
    figures = data.get("figures")
    if not isinstance(figures, list):
        return data
    root = base_dir.resolve()
    for figure in figures:
        if not isinstance(figure, dict) or figure.get("svg"):
            continue
        file = figure.get("file")
        if not isinstance(file, str):
            continue
        slug = figure.get("slug", "?")
        path = (root / file).resolve()
        if root not in path.parents:
            raise ValidationError(f"figure {slug}: file must be inside the pack folder")
        if not path.is_file():
            raise ValidationError(f"figure {slug}: file not found: {file}")
        figure["svg"] = path.read_text(encoding="utf-8")
    return data


def load_pack_file(path: Path) -> ContentPackSpec:
    """A pack file with its figure drawings read in. Raises ValidationError like `parse_pack`."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return parse_pack(inline_figure_files(data, path.parent))
