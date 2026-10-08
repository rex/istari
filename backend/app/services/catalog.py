"""Scan the learning share for video courses and keep the result in memory.

A scan walks the configured topic folders (`Cloud/AWS`, `Kubernetes/CKA`, ...) under
`LEARNING_ROOT`. Every directory that holds at least one video is a course; every
directory inside it that holds videos is a section. The walk is read-only and runs in
a worker thread because the share is slow and remote.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import anyio

from app.domain.naming import infer_exam, is_junk_name, natural_key
from app.domain.watch import (
    VIDEO_SUFFIXES,
    Course,
    Lecture,
    Section,
    caption_for,
    course_slug,
    lecture_title,
    section_title,
)


def scan_course(topic: str, course_dir: Path) -> Course | None:
    """The course at `course_dir`, or None when it holds no video at all."""
    sections: dict[str, list[Lecture]] = {}
    for dirpath, dirnames, filenames in os.walk(course_dir):
        dirnames[:] = sorted(
            (d for d in dirnames if not d.startswith(".") and not is_junk_name(d)),
            key=natural_key,
        )
        videos = [f for f in filenames if Path(f).suffix.lower() in VIDEO_SUFFIXES]
        if not videos:
            continue
        siblings = {f.lower(): f for f in filenames}
        relative_dir = Path(dirpath).relative_to(course_dir).as_posix()
        prefix = "" if relative_dir == "." else f"{relative_dir}/"
        lectures: list[Lecture] = []
        for name in sorted(videos, key=natural_key):
            caption = caption_for(Path(name).stem, siblings)
            try:
                size = os.stat(os.path.join(dirpath, name)).st_size
            except OSError:
                size = 0
            lectures.append(
                Lecture(
                    path=f"{prefix}{name}",
                    title=lecture_title(name),
                    caption_path=f"{prefix}{caption}" if caption else None,
                    size_bytes=size,
                )
            )
        sections[relative_dir] = lectures
    if not sections:
        return None
    hint = infer_exam(course_dir.name)
    ordered = sorted(sections.items(), key=lambda item: natural_key(item[0]))
    return Course(
        slug=course_slug(topic, course_dir.name),
        title=course_dir.name,
        topic=topic,
        exam_code=hint.code,
        year=hint.year,
        root=str(course_dir),
        sections=tuple(
            Section(title=section_title(rel), lectures=tuple(lectures)) for rel, lectures in ordered
        ),
    )


def scan_catalog(root: Path, topics: Sequence[str]) -> list[Course]:
    courses: list[Course] = []
    for topic in topics:
        topic_dir = root / topic
        if not topic_dir.is_dir():
            continue
        for child in sorted(topic_dir.iterdir(), key=lambda p: natural_key(p.name)):
            if child.is_dir() and not child.name.startswith(".") and not is_junk_name(child.name):
                course = scan_course(topic, child)
                if course is not None:
                    courses.append(course)
    return courses


@dataclass
class CatalogCache:
    """The last scan, plus a refresh that never runs twice at once."""

    root: Path | None
    topics: tuple[str, ...]
    courses: list[Course] = field(default_factory=list)
    scanned_at: datetime | None = None
    scanning: bool = False
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    @property
    def configured(self) -> bool:
        return self.root is not None and self.root.is_dir()

    def by_slug(self, slug: str) -> Course | None:
        return next((course for course in self.courses if course.slug == slug), None)

    async def refresh(self) -> None:
        if not self.configured or self.root is None:
            return
        async with self._lock:
            self.scanning = True
            try:
                self.courses = await anyio.to_thread.run_sync(scan_catalog, self.root, self.topics)
                self.scanned_at = datetime.now(UTC)
            finally:
                self.scanning = False

    def start_background_refresh(self) -> asyncio.Task[None] | None:
        """Kick off a scan without waiting; the first page load shows `scanning` meanwhile."""
        if not self.configured or self.scanning:
            return None
        return asyncio.create_task(self.refresh())
