"""Courses on the learning share as the player sees them: sections, lectures, captions.

Pure data and naming rules. The filesystem walk lives in `services.catalog`; the player
never copies or modifies anything on the share.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import PurePosixPath

from app.domain.naming import slugify

VIDEO_SUFFIXES = frozenset({".mp4", ".m4v", ".webm", ".mov", ".mkv"})
CAPTION_SUFFIXES = frozenset({".vtt", ".srt"})
MEDIA_TYPES = {
    ".mp4": "video/mp4",
    ".m4v": "video/mp4",
    ".webm": "video/webm",
    ".mov": "video/quicktime",
    ".mkv": "video/x-matroska",
}
_LEADING_NUMBER = re.compile(r"^\s*\d+[\s.\-_)]*")
_CAPTION_VARIANTS = ("", "_en", ".en", "-en", "_english", " english")


@dataclass(frozen=True, slots=True)
class Lecture:
    path: str  # relative to the course root, POSIX separators
    title: str
    caption_path: str | None
    size_bytes: int


@dataclass(frozen=True, slots=True)
class Section:
    title: str
    lectures: tuple[Lecture, ...]


@dataclass(frozen=True, slots=True)
class Course:
    slug: str
    title: str
    topic: str  # e.g. "Cloud/AWS"
    exam_code: str | None
    year: int | None
    root: str  # absolute directory on disk
    sections: tuple[Section, ...]

    def lectures(self) -> Iterator[Lecture]:
        for section in self.sections:
            yield from section.lectures

    @property
    def lecture_count(self) -> int:
        return sum(len(s.lectures) for s in self.sections)

    @property
    def caption_count(self) -> int:
        return sum(1 for lecture in self.lectures() if lecture.caption_path)

    def lecture(self, path: str) -> Lecture | None:
        return next((lecture for lecture in self.lectures() if lecture.path == path), None)


def course_slug(topic: str, name: str) -> str:
    """Readable and unique: the name's slug plus a short hash of its place on the share."""
    digest = hashlib.sha1(f"{topic}/{name}".encode()).hexdigest()[:6]  # noqa: S324 - not security
    return f"{slugify(name, 60)}-{digest}"


def lecture_title(filename: str) -> str:
    stem = PurePosixPath(filename).stem
    return _LEADING_NUMBER.sub("", stem).replace("_", " ").strip() or stem


def section_title(relative_dir: str) -> str:
    return "Lectures" if relative_dir in {"", "."} else relative_dir.replace("/", " / ")


def caption_for(video_stem: str, siblings: dict[str, str]) -> str | None:
    """The caption file for a video among its directory siblings (lowercase name -> name).

    Prefers WebVTT over SRT and the exact stem over language-suffixed variants; falls back
    to any caption whose name starts with the video's stem (" English.vtt" and the like).
    """
    stem = video_stem.lower()
    for suffix in (".vtt", ".srt"):
        for variant in _CAPTION_VARIANTS:
            hit = siblings.get(f"{stem}{variant}{suffix}")
            if hit:
                return hit
    for suffix in (".vtt", ".srt"):
        for lowered, original in sorted(siblings.items()):
            if lowered.endswith(suffix) and lowered.startswith(stem):
                return original
    return None
