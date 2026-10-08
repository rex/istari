"""Operator CLI: `uv run python -m app.cli <command>`.

Commands:
  bootstrap-owner   create the single owner account (password from a prompt or
                    ISTARI_OWNER_PASSWORD); refuses to overwrite unless --reset-password
  seed              import every content/packs/*/pack.json (idempotent)
  import-pack       import one pack file (--dry-run previews changes)
  export-pack       write a pack from the database as JSON
  validate-pack     schema + cross-reference validation only
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.engine import create_engine, dispose_engine
from app.adapters.db.session import session_factory
from app.cli import corpus_cmds
from app.config import settings
from app.domain.content.schemas.pack import ContentPackSpec
from app.domain.content.validate import parse_pack, validate_pack
from app.domain.exceptions import IstariError
from app.services import auth as auth_service
from app.services.content_export import export_pack
from app.services.content_import import ImportReport, import_pack


async def _session() -> tuple[AsyncSession, object]:
    engine = create_engine(settings.database_url, pool_size=1, max_overflow=0)
    return session_factory(engine)(), engine


async def _run(fn: object) -> int:
    """Run a coroutine function(db) inside one transaction with a dedicated engine."""
    db, engine = await _session()
    try:
        async with db:
            async with db.begin():
                result = await fn(db)  # type: ignore[operator]
            return int(result or 0)
    except IstariError as exc:
        print(f"error: {exc.message}", file=sys.stderr)
        if exc.details:
            print(json.dumps(exc.details, indent=2, default=str), file=sys.stderr)
        return 1
    finally:
        await dispose_engine(engine)  # type: ignore[arg-type]


def _read_password(args: argparse.Namespace) -> str:
    env = os.environ.get("ISTARI_OWNER_PASSWORD")
    if env:
        return env
    if not sys.stdin.isatty():
        print("error: set ISTARI_OWNER_PASSWORD when running non-interactively", file=sys.stderr)
        raise SystemExit(2)
    first = getpass.getpass("Owner password: ")
    second = getpass.getpass("Repeat password: ")
    if first != second:
        print("error: passwords do not match", file=sys.stderr)
        raise SystemExit(2)
    return first


def cmd_bootstrap_owner(args: argparse.Namespace) -> int:
    password = _read_password(args)

    async def go(db: AsyncSession) -> int:
        if args.reset_password:
            await auth_service.set_owner_password(db, args.username, password)
            print(f"password updated for {args.username}")
        else:
            await auth_service.create_owner(db, args.username, password)
            print(f"owner {args.username} created")
        return 0

    return asyncio.run(_run(go))


def _print_report(report: ImportReport) -> None:
    label = "DRY RUN" if report.dry_run else "IMPORTED"
    print(f"[{label}] pack {report.pack_slug}: {json.dumps(report.counts())}")
    for key in report.created:
        print(f"  + {key}")
    for key in report.updated:
        print(f"  ~ {key}")
    for key in report.retired:
        print(f"  - {key} (retired)")
    for note in report.track_changes:
        print(f"  ! {note}")
    for warning in report.warnings:
        print(f"  ? {warning}")


def _load_pack(path: Path) -> ContentPackSpec:
    return parse_pack(json.loads(path.read_text(encoding="utf-8")))


def cmd_import(args: argparse.Namespace) -> int:
    spec = _load_pack(Path(args.path))

    async def go(db: AsyncSession) -> int:
        report = await import_pack(db, spec, dry_run=args.dry_run, now=datetime.now(UTC))
        _print_report(report)
        return 0

    return asyncio.run(_run(go))


def cmd_seed(args: argparse.Namespace) -> int:
    root = Path(args.dir or settings.content_packs_dir)
    paths = sorted(root.glob("*/pack.json"))
    if not paths:
        print(f"no packs found under {root}", file=sys.stderr)
        return 1

    async def go(db: AsyncSession) -> int:
        for path in paths:
            spec = _load_pack(path)
            report = await import_pack(db, spec, dry_run=False, now=datetime.now(UTC))
            _print_report(report)
        return 0

    return asyncio.run(_run(go))


def cmd_export(args: argparse.Namespace) -> int:
    rendered: dict[str, str] = {}

    async def go(db: AsyncSession) -> int:
        spec = await export_pack(db, args.slug)
        rendered["text"] = json.dumps(spec.model_dump(mode="json"), indent=2, ensure_ascii=False)
        return 0

    code = asyncio.run(_run(go))
    if code != 0:
        return code
    if args.output:
        Path(args.output).write_text(rendered["text"] + "\n", encoding="utf-8")
        print(f"wrote {args.output}")
    else:
        print(rendered["text"])
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    try:
        spec = parse_pack(json.loads(Path(args.path).read_text(encoding="utf-8")))
    except IstariError as exc:
        print(f"schema errors: {json.dumps(exc.details, indent=2)}", file=sys.stderr)
        return 1
    report = validate_pack(spec)
    print(json.dumps(report.as_dict(), indent=2))
    return 0 if report.ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="istari", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("bootstrap-owner")
    p.add_argument("--username", required=True)
    p.add_argument("--reset-password", action="store_true")
    p.set_defaults(fn=cmd_bootstrap_owner)

    p = sub.add_parser("seed")
    p.add_argument("--dir", default=None)
    p.set_defaults(fn=cmd_seed)

    p = sub.add_parser("import-pack")
    p.add_argument("path")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(fn=cmd_import)

    p = sub.add_parser("export-pack")
    p.add_argument("slug")
    p.add_argument("-o", "--output", default=None)
    p.set_defaults(fn=cmd_export)

    corpus_cmds.register(sub)

    p = sub.add_parser("validate-pack")
    p.add_argument("path")
    p.set_defaults(fn=cmd_validate)

    args = parser.parse_args(argv)
    result: int = args.fn(args)
    return result
