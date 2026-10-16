"""Build the lecture-to-objective index for a track.

Candidate courses are the catalog's courses on the track's subject (the topic folder names
it) or in its exam family (an SAA-C02 course counts for SAA-C03). Their captions are read
off the share in a worker thread, each lecture becomes term counts, and every lecture is
ranked against the track's objectives. `rule` and `lexical` rows are rewritten by every
run; `pinned` and `excluded` rows are the owner's and stay.
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import anyio
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.adapters.db.models import (
    Certification,
    Domain,
    ExamVersion,
    IndexedLecture,
    LectureIndexRun,
    LectureObjective,
    Objective,
    Subject,
)
from app.corpus.captions import caption_duration_seconds, caption_lines
from app.domain.clock import Clock
from app.domain.lecture_index import (
    GENERIC_SHARE,
    MASS_POWER,
    Index,
    Query,
    objective_query,
    query_mass,
    rank_lecture,
    specificity,
)
from app.domain.lecture_rules import (
    distinctive_domain_terms,
    domain_hints,
    is_housekeeping,
    rule_codes,
)
from app.domain.lecture_text import document
from app.domain.watch import Course, Lecture
from app.services.catalog import CatalogCache
from app.services.content_query import content_str, list_items, objective_codes_for_items
from app.services.course_currency import exam_family, own_exam
from app.services.learning_path import compose_paths

log = logging.getLogger("istari.lectures")

EXCERPT_CHARS = 600
OWNER_SOURCES = ("pinned", "excluded")
MACHINE_SOURCES = ("rule", "lexical")


def candidate_courses(catalog: CatalogCache, *, exam_code: str, subject_slug: str) -> list[Course]:
    """Courses worth ranking for a track: same exam family, or filed under the subject."""
    family = exam_family(exam_code)
    subject = subject_slug.lower()
    chosen: list[Course] = []
    for course in catalog.courses:
        topic_parts = {part.lower() for part in course.topic.replace("-", "/").split("/")}
        if (family and exam_family(course.exam_code) == family) or subject in topic_parts:
            chosen.append(course)
    return chosen


@dataclass(slots=True)
class _Read:
    course: Course
    section_title: str
    lecture: Lecture
    text: str | None
    duration: float | None


def _read_captions(course: Course, lecture: Lecture) -> tuple[str | None, float | None]:
    if lecture.caption_path is None:
        return None, None
    root = Path(course.root).resolve()
    target = (root / lecture.caption_path).resolve()
    if not target.is_relative_to(root) or not target.is_file():
        return None, None
    raw = target.read_text(encoding="utf-8", errors="replace")
    return " ".join(caption_lines(raw)), caption_duration_seconds(raw)


def _read_all(courses: list[Course]) -> list[_Read]:
    reads: list[_Read] = []
    for course in courses:
        for section in course.sections:
            for lecture in section.lectures:
                text, duration = _read_captions(course, lecture)
                reads.append(_Read(course, section.title, lecture, text, duration))
    return reads


async def track_subject(db: AsyncSession, exam: ExamVersion) -> str:
    """The slug of the track's subject ("aws"), the folder name its courses are filed under."""
    slug = await db.scalar(
        select(Subject.slug)
        .join(Certification, Certification.subject_id == Subject.id)
        .where(Certification.id == exam.certification_id)
    )
    return slug or ""


async def objective_queries(
    db: AsyncSession,
    exam_version_id: int,
    *,
    body_weight: float = 1.0,
    stem_weight: float = 1.0,
) -> tuple[list[Query], dict[str, Objective], dict[str, str]]:
    """One weighted query per objective of the track, with the objectives and domain names."""
    rows = (
        await db.execute(
            select(Objective, Domain)
            .join(Domain, Domain.id == Objective.domain_id)
            .where(Domain.exam_version_id == exam_version_id)
            .order_by(Domain.code, Objective.code)
        )
    ).all()
    lesson_titles: dict[str, list[str]] = defaultdict(list)
    lesson_bodies: dict[str, list[str]] = defaultdict(list)
    stems: dict[str, list[str]] = defaultdict(list)
    for kind, titles, bodies in (
        ("lesson", lesson_titles, lesson_bodies),
        ("question", None, stems),
    ):
        items = await list_items(db, exam_version_id=exam_version_id, kind=kind)
        codes = await objective_codes_for_items(db, [item.id for item, _ in items])
        for item, rev in items:
            for code in codes.get(item.id, []):
                if titles is not None:
                    titles[code].append(content_str(rev, "title"))
                    bodies[code].append(content_str(rev, "body_md"))
                else:
                    bodies[code].append(content_str(rev, "stem_md"))
    queries: list[Query] = []
    objectives: dict[str, Objective] = {}
    domains: dict[str, str] = {}
    for objective, domain in rows:
        domains[domain.code] = domain.name
        objectives[objective.code] = objective
        queries.append(
            objective_query(
                objective.code,
                domain.code,
                objective.title,
                [*objective.knowledge, *objective.skills],
                lesson_titles.get(objective.code, []),
                lesson_bodies.get(objective.code, []),
                stems.get(objective.code, []),
                body_weight=body_weight,
                stem_weight=stem_weight,
            )
        )
    return queries, objectives, domains


async def _upsert_lectures(db: AsyncSession, reads: list[_Read], now: datetime) -> None:
    slugs = {read.course.slug for read in reads}
    existing = {
        (row.course_slug, row.lecture_path): row
        for row in (
            await db.scalars(
                select(IndexedLecture).where(IndexedLecture.course_slug.in_(list(slugs)))
            )
        ).all()
    }
    for read in reads:
        if read.text is None:
            continue
        doc = document("", read.text)
        row = existing.get((read.course.slug, read.lecture.path))
        if row is None:
            row = IndexedLecture(course_slug=read.course.slug, lecture_path=read.lecture.path)
            db.add(row)
        row.course_title = read.course.title[:300]
        row.section_title = read.section_title[:300]
        row.lecture_title = read.lecture.title[:300]
        row.topic = read.course.topic[:120]
        row.exam_code = read.course.exam_code
        row.year = read.course.year
        row.duration_seconds = read.duration
        row.word_count = doc.length
        row.excerpt = read.text[:EXCERPT_CHARS]
        row.terms = dict(doc.terms)
        row.indexed_at = now
    await db.flush()


async def build_index(
    db: AsyncSession, catalog: CatalogCache, exam: ExamVersion, *, clock: Clock
) -> LectureIndexRun:
    """One run: read, rank, rewrite the machine rows; the owner's rows are untouched."""
    now = clock.now()
    run = LectureIndexRun(exam_version_id=exam.id, status="running")
    db.add(run)
    await db.flush()
    try:
        courses = candidate_courses(
            catalog, exam_code=exam.code, subject_slug=await track_subject(db, exam)
        )
        reads = await anyio.to_thread.run_sync(_read_all, courses)
        queries, objectives, domains = await objective_queries(db, exam.id)
        spec = specificity(queries)
        distinctive = distinctive_domain_terms(domains)
        await _upsert_lectures(db, reads, now)

        owned = {
            (row.course_slug, row.lecture_path, row.objective_id)
            for row in (
                await db.scalars(
                    select(LectureObjective).where(
                        LectureObjective.exam_version_id == exam.id,
                        LectureObjective.source.in_(OWNER_SOURCES),
                    )
                )
            ).all()
        }
        await db.execute(
            delete(LectureObjective).where(
                LectureObjective.exam_version_id == exam.id,
                LectureObjective.source.in_(MACHINE_SOURCES),
            )
        )
        docs = {
            (read.course.slug, read.lecture.path): document(read.lecture.path, read.text)
            for read in reads
            if read.text is not None
        }
        index = Index(docs.values())
        generic = index.generic(GENERIC_SHARE)
        mass = {query.code: query_mass(query, spec) for query in queries}
        first_sections = {
            course.slug: course.sections[0].title if course.sections else "" for course in courses
        }
        mappings = 0
        for read in reads:
            key = (read.course.slug, read.lecture.path)
            titles = [read.lecture.title, read.lecture.path, read.section_title]
            placed: set[str] = set()
            # A welcome or a tour of the course teaches no objective; it maps to nothing.
            if is_housekeeping(
                read.lecture.title,
                first_section=read.section_title == first_sections.get(read.course.slug),
            ):
                continue
            # A code in a file name names this track's objective only in a course for this
            # exam; another exam's "(OBJ 4.3)" is that exam's objective.
            codes = rule_codes(titles, objectives) if own_exam(read.course, exam) else []
            for code in codes:
                if (*key, objectives[code].id) in owned:
                    continue
                db.add(_mapping(exam.id, key, objectives[code].id, "rule", 1.0, 1.0, []))
                placed.add(code)
                mappings += 1
            doc = docs.get(key)
            if doc is None:
                continue
            hints = domain_hints(titles, distinctive)
            for hit in rank_lecture(
                index, doc, queries, spec, hints, generic=generic, mass=mass, mass_power=MASS_POWER
            ):
                objective_id = objectives[hit.code].id
                if hit.code in placed or (*key, objective_id) in owned:
                    continue
                db.add(
                    _mapping(
                        exam.id,
                        key,
                        objective_id,
                        "lexical",
                        hit.score,
                        hit.normalized,
                        list(hit.matched),
                    )
                )
                mappings += 1
        run.candidate_courses = len(courses)
        run.lectures_total = len(reads)
        run.lectures_with_captions = sum(1 for read in reads if read.lecture.caption_path)
        run.lectures_indexed = len(docs)
        run.mappings = mappings
        # The paths are derived from the mappings, so every index run recomposes them.
        await compose_paths(db, catalog, exam, now=now)
        run.status = "done"
    except Exception as exc:
        log.exception("lecture index build failed", extra={"event": "lectures.index.failed"})
        run.status = "failed"
        run.error = str(exc)[:1000]
    run.finished_at = clock.now()
    await db.flush()
    log.info(
        "lecture index built",
        extra={
            "event": "lectures.index",
            "status": run.status,
            "lectures": run.lectures_indexed,
            "mappings": run.mappings,
        },
    )
    return run


def _mapping(
    exam_version_id: int,
    key: tuple[str, str],
    objective_id: int,
    source: str,
    score: float,
    normalized: float,
    matched: list[str],
) -> LectureObjective:
    return LectureObjective(
        exam_version_id=exam_version_id,
        course_slug=key[0],
        lecture_path=key[1],
        objective_id=objective_id,
        source=source,
        score=score,
        normalized=normalized,
        matched_terms=list(matched),
    )


@dataclass
class IndexRunner:
    """One build at a time, in the background, with its own session; status is in the db.

    Each run rescans the catalog before it builds, so the index never depends on a page
    having been opened first and picks up what landed on the share since the last run.
    """

    task: asyncio.Task[None] | None = None
    last_error: str | None = field(default=None)

    @property
    def running(self) -> bool:
        return self.task is not None and not self.task.done()

    def start(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        catalog: CatalogCache,
        exam_version_id: int,
        clock: Clock,
    ) -> bool:
        if self.running:
            return False

        async def go() -> None:
            try:
                # Rescan the share first: a rebuild is how new courses and captions get in.
                await catalog.refresh()
                async with session_factory() as db, db.begin():
                    exam = await db.get(ExamVersion, exam_version_id)
                    if exam is not None:
                        await build_index(db, catalog, exam, clock=clock)
                self.last_error = None
            except Exception as exc:
                self.last_error = str(exc)[:500]
                log.exception("lecture index task failed", extra={"event": "lectures.index"})

        self.task = asyncio.create_task(go())
        return True
