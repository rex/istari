"""Compose a learning path for one objective from the lectures mapped to it.

Continuity first: the course with the deepest coverage of the objective supplies a run of
its lectures in course order; the other courses' strongest lectures fill in behind it; a
course for an older version of the exam steps aside when a current one covers the same
ground; the whole thing is capped by minutes. The owner's pins lead and his exclusions never
return. No merged video: every entry is one lecture of one course, named as such.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Collection, Iterable, Sequence
from dataclasses import dataclass

from app.domain.naming import natural_key

CAP_MINUTES = 120.0
# A lecture whose length is unknown still takes time; this is what it costs against the cap.
FALLBACK_MINUTES = 8.0
# An older-exam course steps aside when a current one has at least this share of its minutes.
STALE_COVERAGE = 0.5
CURRENCY_RANK = {"current": 0, "same_exam": 1, "newer": 2, "older": 3, "other": 4, "unknown": 5}
SOURCE_RANK = {"pinned": 0, "rule": 1, "lexical": 2}
_NOISE = re.compile(r"[^a-z0-9]+")

Key = tuple[str, str]


@dataclass(frozen=True, slots=True)
class PathLecture:
    course_slug: str
    course_title: str
    lecture_path: str
    lecture_title: str
    minutes: float
    score: float
    source: str
    currency: str
    section_title: str = ""

    @property
    def key(self) -> Key:
        return (self.course_slug, self.lecture_path)

    @property
    def cost(self) -> float:
        return self.minutes if self.minutes > 0 else FALLBACK_MINUTES


@dataclass(frozen=True, slots=True)
class PathEntry:
    course_slug: str
    lecture_path: str
    reason: str
    minutes: float
    source: str


def _ground(title: str) -> str:
    return _NOISE.sub(" ", title.lower()).strip()


def _length(lectures: Iterable[PathLecture]) -> float:
    return sum(lecture.cost for lecture in lectures)


def _depth(lectures: Iterable[PathLecture]) -> float:
    """Minutes weighted by how strongly each lecture maps: coverage, not just length."""
    return sum(lecture.score * lecture.cost for lecture in lectures)


def _minutes(value: float) -> str:
    whole = round(value)
    return f"{whole // 60} h {whole % 60:02d} min" if whole >= 60 else f"{whole} min"


def _anchor(courses: dict[str, list[PathLecture]]) -> str:
    """The deepest course, preferring one made for this exam when it has at least half the
    depth of the deepest of all: a course built around the objectives beats a longer one."""
    by_depth = sorted(
        courses,
        key=lambda slug: (
            -_depth(courses[slug]),
            CURRENCY_RANK.get(courses[slug][0].currency, 5),
            -len(courses[slug]),
            slug,
        ),
    )
    best = _depth(courses[by_depth[0]])
    own = [slug for slug in by_depth if CURRENCY_RANK.get(courses[slug][0].currency, 5) <= 3]
    if own and _depth(courses[own[0]]) >= STALE_COVERAGE * best:
        return own[0]
    return by_depth[0]


def _run(lectures: Iterable[PathLecture]) -> list[PathLecture]:
    """A course's lectures in course order, its most relevant sections first, so the run
    starts where the objective is taught rather than at the course's welcome."""
    sections: dict[str, list[PathLecture]] = defaultdict(list)
    for lecture in sorted(lectures, key=lambda item: natural_key(item.lecture_path)):
        sections[lecture.section_title].append(lecture)

    def relevance(group: list[PathLecture]) -> float:
        return _depth(group) / _length(group)

    ordered = sorted(
        sections.values(),
        key=lambda group: (-relevance(group), natural_key(group[0].lecture_path)),
    )
    return [lecture for group in ordered for lecture in group]


def stale_courses(lectures: Iterable[PathLecture]) -> list[str]:
    """Older-exam courses a current one covers: titles, deepest first."""
    courses: dict[str, list[PathLecture]] = defaultdict(list)
    for lecture in lectures:
        courses[lecture.course_slug].append(lecture)
    current = max(
        (
            _depth(group)
            for group in courses.values()
            if CURRENCY_RANK.get(group[0].currency, 5) <= 1
        ),
        default=0.0,
    )
    stale = [
        group
        for group in courses.values()
        if group[0].currency == "older"
        and current > 0
        and current >= STALE_COVERAGE * _depth(group)
    ]
    stale.sort(key=lambda group: -_depth(group))
    return [group[0].course_title for group in stale]


def _fill_reason(lecture: PathLecture) -> str:
    if lecture.source == "pinned":
        return f"{lecture.course_title}: you mapped it to this objective"
    if lecture.source == "rule":
        return f"{lecture.course_title}: the objective is named in the lecture title"
    return f"{lecture.course_title}: the strongest match left ({lecture.score:.0%})"


def compose_path(
    lectures: Sequence[PathLecture],
    *,
    cap_minutes: float = CAP_MINUTES,
    pinned: Sequence[Key] = (),
    excluded: Collection[Key] = (),
) -> list[PathEntry]:
    """The owner's pins in his order, then the anchor course's run, then the fill."""
    by_key = {lecture.key: lecture for lecture in lectures}
    entries: list[PathEntry] = []
    used: set[Key] = set()
    grounds: set[str] = set()
    total = 0.0

    def take(lecture: PathLecture, reason: str, source: str) -> None:
        nonlocal total
        entries.append(
            PathEntry(lecture.course_slug, lecture.lecture_path, reason, lecture.minutes, source)
        )
        used.add(lecture.key)
        grounds.add(_ground(lecture.lecture_title))
        total += lecture.cost

    for key in pinned:
        lecture = by_key.get(key)
        if lecture is not None and key not in excluded and key not in used:
            take(lecture, "pinned by you", "pinned")

    stale = set(stale_courses(lectures))
    courses: dict[str, list[PathLecture]] = defaultdict(list)
    for lecture in lectures:
        if lecture.key in excluded or lecture.key in used or lecture.course_title in stale:
            continue
        courses[lecture.course_slug].append(lecture)
    if not courses:
        return entries

    anchor_slug = _anchor(courses)
    anchor = _run(courses[anchor_slug])
    depth = _minutes(_length(anchor))
    for lecture in anchor:
        if total >= cap_minutes:
            break
        take(
            lecture,
            f"{lecture.course_title}: the deepest coverage of this objective ({depth})",
            "proposed",
        )

    fill = sorted(
        (lecture for slug, group in courses.items() if slug != anchor_slug for lecture in group),
        key=lambda lecture: (
            SOURCE_RANK.get(lecture.source, 9),
            -lecture.score,
            CURRENCY_RANK.get(lecture.currency, 5),
            lecture.course_slug,
            natural_key(lecture.lecture_path),
        ),
    )
    for lecture in fill:
        if total >= cap_minutes:
            break
        if _ground(lecture.lecture_title) in grounds and lecture.source != "pinned":
            continue
        take(lecture, _fill_reason(lecture), "proposed")
    return entries
