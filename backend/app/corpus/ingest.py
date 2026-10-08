"""Walk one course directory and write a private Markdown corpus with a manifest.

Output layout, under the gitignored corpus root:

    corpus/<course-slug>/<section-slug>/<lecture-slug>.md
    corpus/<course-slug>/manifest.json

Each Markdown file starts with a small front matter block naming its source path,
kind and word count. The manifest records the course, the exam code and year inferred
from its name, every file written and every file skipped with the reason.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from app.corpus.convert import CAPTION_SUFFIXES, SUPPORTED_SUFFIXES, ConversionError, convert_file
from app.domain.naming import infer_exam, is_junk_name, slugify

MIN_WORDS = 15


@dataclass(slots=True)
class IngestReport:
    course: str
    out_dir: Path
    written: list[dict[str, object]] = field(default_factory=list)
    skipped: list[dict[str, str]] = field(default_factory=list)

    def counts(self) -> dict[str, int]:
        words = sum(int(entry["words"]) for entry in self.written)  # type: ignore[call-overload]
        return {"written": len(self.written), "skipped": len(self.skipped), "words": words}


def _target_for(out_dir: Path, relative: Path) -> Path:
    section = "/".join(slugify(part) for part in relative.parent.parts)
    return out_dir / section / f"{slugify(relative.stem)}.md"


def ingest_course(src: Path, out_root: Path, *, course: str | None = None) -> IngestReport:
    """Convert every supported file under `src`; never modifies `src`."""
    name = course or src.name
    out_dir = out_root / slugify(name)
    report = IngestReport(course=name, out_dir=out_dir)
    seen_targets: dict[Path, str] = {}

    for path in sorted(p for p in src.rglob("*") if p.is_file()):
        relative = path.relative_to(src)
        suffix = path.suffix.lower()
        if suffix not in SUPPORTED_SUFFIXES or is_junk_name(path.name):
            report.skipped.append({"source": relative.as_posix(), "reason": "not course text"})
            continue
        target = _target_for(out_dir, relative)
        if target in seen_targets and suffix in CAPTION_SUFFIXES:
            report.skipped.append(
                {"source": relative.as_posix(), "reason": f"duplicate of {seen_targets[target]}"}
            )
            continue
        try:
            text = convert_file(path).strip()
        except ConversionError as exc:
            report.skipped.append({"source": relative.as_posix(), "reason": str(exc)})
            continue
        words = len(text.split())
        if words < MIN_WORDS:
            report.skipped.append({"source": relative.as_posix(), "reason": "too short"})
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        header = f"---\nsource: {relative.as_posix()}\nkind: {suffix[1:]}\nwords: {words}\n---\n\n"
        target.write_text(header + text + "\n", encoding="utf-8")
        seen_targets[target] = relative.as_posix()
        report.written.append(
            {
                "path": target.relative_to(out_dir).as_posix(),
                "source": relative.as_posix(),
                "kind": suffix[1:],
                "words": words,
            }
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "course": name,
        "source_dir": str(src),
        "exam": asdict(infer_exam(name)),
        "ingested_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "counts": report.counts(),
        "files": report.written,
        "skipped": report.skipped,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return report


def ingest_tree(root: Path, out_root: Path) -> list[IngestReport]:
    """Every child directory of `root` is a course; a loose file at the top is one too.

    This is the shape of a topic folder on the learning share (`Cloud/AWS`,
    `Kubernetes/CKA`): course folders side by side with single PDFs and EPUBs.
    """
    reports: list[IngestReport] = []
    for child in sorted(root.iterdir(), key=lambda p: p.name.casefold()):
        if child.name.startswith(".") or is_junk_name(child.name):
            continue
        if child.is_dir():
            reports.append(ingest_course(child, out_root))
        elif child.suffix.lower() in SUPPORTED_SUFFIXES:
            report = IngestReport(course=child.stem, out_dir=out_root / slugify(child.stem))
            try:
                text = convert_file(child).strip()
            except ConversionError as exc:
                report.skipped.append({"source": child.name, "reason": str(exc)})
            else:
                words = len(text.split())
                report.out_dir.mkdir(parents=True, exist_ok=True)
                target = report.out_dir / f"{slugify(child.stem)}.md"
                header = (
                    f"---\nsource: {child.name}\nkind: {child.suffix[1:]}\nwords: {words}\n---\n\n"
                )
                target.write_text(header + text + "\n", encoding="utf-8")
                report.written.append(
                    {
                        "path": target.name,
                        "source": child.name,
                        "kind": child.suffix[1:],
                        "words": words,
                    }
                )
            reports.append(report)
    return reports
