"""File-to-text conversion for the corpus: captions natively, documents via local tools.

pandoc converts HTML, EPUB and DOCX to GitHub-flavoured Markdown; pdftotext (poppler)
extracts PDF text. Both are looked up on PATH at call time, so a missing tool is a
clear error for that file rather than a crash of the whole run.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from app.corpus.captions import caption_text

CAPTION_SUFFIXES = frozenset({".srt", ".vtt"})
TEXT_SUFFIXES = frozenset({".md", ".txt"})
DOCUMENT_SUFFIXES = frozenset({".html", ".htm", ".pdf", ".epub", ".docx"})
SUPPORTED_SUFFIXES = CAPTION_SUFFIXES | TEXT_SUFFIXES | DOCUMENT_SUFFIXES

_TOOL_TIMEOUT_SECONDS = 600


class ConversionError(RuntimeError):
    """A file could not be converted; the message says why."""


def _run_tool(tool: str, args: list[str]) -> str:
    exe = shutil.which(tool)
    if exe is None:
        raise ConversionError(f"{tool} is not installed (brew install {tool})")
    try:
        result = subprocess.run(  # noqa: S603 - fixed executable, file path as argument
            [exe, *args],
            capture_output=True,
            text=True,
            timeout=_TOOL_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ConversionError(f"{tool} timed out after {_TOOL_TIMEOUT_SECONDS}s") from exc
    if result.returncode != 0:
        detail = result.stderr.strip().splitlines()[-1:] or ["no output"]
        raise ConversionError(f"{tool} failed: {detail[0][:200]}")
    return result.stdout


def pandoc_to_markdown(path: Path, source_format: str) -> str:
    return _run_tool("pandoc", ["-f", source_format, "-t", "gfm", "--wrap=none", str(path)])


def pdf_to_text(path: Path, *, layout: bool = True) -> str:
    """Page text. `layout` keeps columns for reading; plain mode suits structured parsing."""
    args = ["-layout", str(path), "-"] if layout else [str(path), "-"]
    return _run_tool("pdftotext", args)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def convert_file(path: Path) -> str:
    """Text for any supported file. Raises ConversionError for unsupported or failed ones."""
    suffix = path.suffix.lower()
    if suffix in CAPTION_SUFFIXES:
        return caption_text(read_text(path))
    if suffix in TEXT_SUFFIXES:
        return read_text(path)
    if suffix in {".html", ".htm"}:
        return pandoc_to_markdown(path, "html")
    if suffix == ".epub":
        return pandoc_to_markdown(path, "epub")
    if suffix == ".docx":
        return pandoc_to_markdown(path, "docx")
    if suffix == ".pdf":
        return pdf_to_text(path)
    raise ConversionError(f"unsupported file type {suffix or '(none)'}")
