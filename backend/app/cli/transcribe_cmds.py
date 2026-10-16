"""`transcribe`: generated captions for the lectures that have none.

    uv run python -m app.cli transcribe "/Volumes/.../Some Course" --to-share
    uv run python -m app.cli transcribe "/Volumes/.../Cloud/AWS" --all --out ../corpus --limit 3

Nothing is written next to a video unless `--to-share` is given; without it the VTTs land
under `--out/<course-slug>/captions/`, which is gitignored. The long run is the owner's call.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.corpus.transcribe import (
    DEFAULT_MODEL,
    Report,
    detect_backend,
    transcribe_course,
    transcribe_tree,
)
from app.domain.naming import slugify


def _print(report: Report) -> None:
    print(
        f"{report.course}: {len(report.done)} transcribed, {report.skipped} already captioned, "
        f"{len(report.failed)} failed",
        flush=True,
    )
    for relative, error in report.failed:
        print(f"  failed {relative}: {error}", file=sys.stderr)


def cmd_transcribe(args: argparse.Namespace) -> int:
    src = Path(args.src).expanduser()
    if not src.is_dir():
        print(f"error: not a directory: {src}", file=sys.stderr)
        return 2
    try:
        backend = detect_backend(
            args.model,
            preferred=args.backend,
            model_dir=Path(args.model_dir).expanduser() if args.model_dir else None,
        )
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if backend.model_path is not None and not backend.model_path.is_file():
        print(f"error: whisper.cpp model not found: {backend.model_path}", file=sys.stderr)
        return 2
    out_root = None if args.to_share else Path(args.out).resolve()
    print(f"{backend.name} ({backend.model}) -> {'the share' if out_root is None else out_root}")
    if args.all:
        reports = transcribe_tree(src, backend, out_root=out_root, limit=args.limit)
    else:
        out_dir = None if out_root is None else out_root / slugify(src.name) / "captions"
        reports = [transcribe_course(src, backend, out_dir=out_dir, limit=args.limit)]
    for report in reports:
        _print(report)
    return 1 if any(report.failed for report in reports) else 0


def register(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    p = sub.add_parser("transcribe", help="Whisper captions for lectures that have none")
    p.add_argument("src", help="a course directory, or a topic folder with --all")
    p.add_argument("--all", action="store_true", help="every course directory under src")
    p.add_argument("--to-share", action="store_true", help="write <lecture>.vtt next to the video")
    p.add_argument("--out", default="../corpus", help="corpus root when not writing to the share")
    p.add_argument(
        "--model",
        default=None,
        help=(
            "the backend's model; default mlx-community/parakeet-tdt-0.6b-v3 for parakeet, "
            f"{DEFAULT_MODEL} for the Whisper backends"
        ),
    )
    p.add_argument("--backend", choices=("auto", "parakeet", "cpp", "openai"), default="auto")
    p.add_argument("--model-dir", default=None, help="where whisper.cpp's ggml-*.bin files are")
    p.add_argument("--limit", type=int, default=None, help="lectures per course, for a trial")
    p.set_defaults(fn=cmd_transcribe)
