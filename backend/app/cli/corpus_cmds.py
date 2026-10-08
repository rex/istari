"""`corpus-ingest` and `corpus-udemy`: purchased course material to private text and packs.

    uv run python -m app.cli corpus-ingest "/Volumes/.../Some Course" --out ../corpus
    uv run python -m app.cli corpus-udemy quiz1.html quiz2.html test1.pdf \
        --exam SOA-C02 --slug udemy-sysops-2021 --name "SysOps 2021 quizzes" \
        --vendor "Udemy course" --out ../content/private/udemy-sysops-2021.json

Both write only under their `--out` path, which is gitignored by default.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from app.corpus.convert import pdf_to_text
from app.corpus.ingest import IngestReport, ingest_course, ingest_tree
from app.corpus.private_pack import ParsedQuestion, PrivatePackMeta, build_private_pack
from app.corpus.udemy_quiz import parse_quiz_html
from app.corpus.udemy_results import parse_results_text
from app.domain.content.validate import parse_pack, validate_pack
from app.domain.exceptions import IstariError
from app.domain.naming import slugify

CERTIFICATIONS = {
    "CLF": ("aws-certified-cloud-practitioner", "AWS Certified Cloud Practitioner"),
    "SAA": (
        "aws-certified-solutions-architect-associate",
        "AWS Certified Solutions Architect - Associate",
    ),
    "SOA": (
        "aws-certified-sysops-administrator-associate",
        "AWS Certified SysOps Administrator - Associate",
    ),
    "DVA": ("aws-certified-developer-associate", "AWS Certified Developer - Associate"),
    "DOP": (
        "aws-certified-devops-engineer-professional",
        "AWS Certified DevOps Engineer - Professional",
    ),
    "SAP": (
        "aws-certified-solutions-architect-professional",
        "AWS Certified Solutions Architect - Professional",
    ),
    "SCS": ("aws-certified-security-specialty", "AWS Certified Security - Specialty"),
    "ANS": (
        "aws-certified-advanced-networking-specialty",
        "AWS Certified Advanced Networking - Specialty",
    ),
    "MLS": (
        "aws-certified-machine-learning-specialty",
        "AWS Certified Machine Learning - Specialty",
    ),
}
_QUIZ_NOISE = re.compile(r"^\d+\s*|\[quiz\]\s*|\s*quiz\s*$", re.I)


def quiz_group(path: Path) -> str:
    """The group a file's questions belong to: "095 [quiz] S3 Quiz.html" -> "S3"."""
    stem = path.stem.split(" (")[0]
    return _QUIZ_NOISE.sub("", stem).strip() or path.stem


def _print_ingest(report: IngestReport) -> None:
    print(f"{report.course}: {json.dumps(report.counts())} -> {report.out_dir}", flush=True)
    reasons = Counter(entry["reason"].split(":")[0] for entry in report.skipped)
    for reason, count in reasons.most_common(4):
        print(f"  skipped {count}: {reason}", flush=True)


def cmd_corpus_ingest(args: argparse.Namespace) -> int:
    src = Path(args.src).expanduser()
    if not src.is_dir():
        print(f"error: {src} is not a directory", file=sys.stderr)
        return 2
    out_root = Path(args.out).expanduser()
    if args.all:
        reports = ingest_tree(src, out_root)
        for report in reports:
            _print_ingest(report)
        total = sum(r.counts()["written"] for r in reports)
        print(f"{len(reports)} resources, {total} files written under {out_root}")
        return 0
    _print_ingest(ingest_course(src, out_root, course=args.course))
    return 0


def _parse_inputs(paths: list[str]) -> list[ParsedQuestion]:
    questions: list[ParsedQuestion] = []
    for raw in paths:
        path = Path(raw).expanduser()
        suffix = path.suffix.lower()
        if suffix in {".html", ".htm"}:
            found = parse_quiz_html(
                path.read_text(encoding="utf-8", errors="replace"), group=quiz_group(path)
            )
        elif suffix == ".pdf":
            found = parse_results_text(pdf_to_text(path, layout=False), group=quiz_group(path))
        else:
            print(f"  ignored {path.name}: not a quiz export", file=sys.stderr)
            continue
        print(f"  {path.name}: {len(found)} questions")
        questions.extend(found)
    return questions


def cmd_corpus_udemy(args: argparse.Namespace) -> int:
    prefix = args.exam.split("-")[0].upper()
    cert_slug, cert_name = CERTIFICATIONS.get(prefix, (f"aws-{slugify(args.exam)}", args.exam))
    meta = PrivatePackMeta(
        slug=args.slug,
        name=args.name,
        vendor=args.vendor,
        exam_code=args.exam.upper(),
        exam_name=f"{cert_name} ({args.exam.upper()})",
        certification_slug=cert_slug,
        certification_name=cert_name,
        authored_on=datetime.now(UTC).date(),
        source_title=f"{args.vendor}: {args.name}",
    )
    questions = _parse_inputs(args.inputs)
    pack, rejected = build_private_pack(questions, meta)
    try:
        report = validate_pack(parse_pack(pack))
    except IstariError as exc:
        print(f"error: {exc.message}", file=sys.stderr)
        print(json.dumps(exc.details, indent=2, default=str), file=sys.stderr)
        return 1
    out = Path(args.out).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(pack, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    kept = len(pack["questions"])  # type: ignore[arg-type]
    print(f"parsed {len(questions)}, kept {kept}, rejected {len(rejected)} -> {out}")
    for reason, count in Counter(reason for _, reason in rejected).most_common():
        print(f"  rejected {count}: {reason}")
    for issue in report.warnings:
        print(f"  warning: {issue.message}")
    for issue in report.errors:
        print(f"  error: {issue.message}", file=sys.stderr)
    return 0 if report.ok else 1


def register(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    p = sub.add_parser("corpus-ingest", help="course directory -> private Markdown corpus")
    p.add_argument("src")
    p.add_argument("--out", default="../corpus", help="corpus root (gitignored)")
    p.add_argument("--course", help="course name; defaults to the directory name")
    p.add_argument(
        "--all",
        action="store_true",
        help="treat src as a topic folder: each child directory (or loose file) is a course",
    )
    p.set_defaults(fn=cmd_corpus_ingest)

    p = sub.add_parser("corpus-udemy", help="Udemy quiz HTML / results PDF -> private pack")
    p.add_argument("inputs", nargs="+")
    p.add_argument("--exam", required=True, help="exam code, e.g. SOA-C02")
    p.add_argument("--slug", required=True, help="pack slug, e.g. udemy-sysops-2021")
    p.add_argument("--name", required=True, help="pack name shown in the app")
    p.add_argument("--vendor", default="Udemy course", help="recorded as the author")
    p.add_argument("--out", required=True, help="pack JSON path (content/private/ is gitignored)")
    p.set_defaults(fn=cmd_corpus_udemy)
