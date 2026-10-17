"""`figures`: render each pack's figure scripts to SVG, or check the committed drawings.

    uv run --group figures python -m app.cli figures render [--pack <slug>]
    uv run --group figures python -m app.cli figures check [--pack <slug>]

A figure's source is `content/packs/<pack>/figures/<slug>.py`: a mingrammer/diagrams script
that writes `<slug>.svg` beside itself with its icons inlined. `render` runs each script in
place and then rewrites the node ids the library draws at random into stable ones, so the
committed drawing only changes when the drawing changes; `check` renders each script in a
scratch copy and compares, so a committed SVG never drifts from its script.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from app.config import settings
from app.domain.content.load import load_pack_file
from app.domain.content.validate import validate_pack
from app.domain.exceptions import IstariError

_RANDOM_ID = re.compile(r"\b[0-9a-f]{32}\b")
_COMMENT = re.compile(r"<!--.*?-->\n?", re.S)


def figure_scripts(packs_dir: Path, pack: str | None = None) -> list[Path]:
    """Every `figures/*.py` under the packs (or one pack), in a stable order, as absolute
    paths: the scripts run with their own folder as the working directory."""
    packs_dir = packs_dir.resolve()
    packs = (
        [packs_dir / pack]
        if pack
        else sorted(path for path in packs_dir.iterdir() if path.is_dir())
    )
    return [script for path in packs for script in sorted((path / "figures").glob("*.py"))]


def stabilize(svg: str) -> str:
    """The drawing with the random node ids replaced by n1, n2, ... in order of appearance,
    and without the generator's comments (they carry its version)."""
    ids: dict[str, str] = {}

    def name(match: re.Match[str]) -> str:
        return ids.setdefault(match.group(0), f"n{len(ids) + 1}")

    return _COMMENT.sub("", _RANDOM_ID.sub(name, svg))


def render(script: Path, *, into: Path | None = None) -> Path:
    """Run a figure script where it lives, or as a copy in `into`, stabilize what it wrote
    and return the SVG's path."""
    target = script
    if into is not None:
        target = into / script.name
        shutil.copy2(script, target)
    subprocess.run(  # noqa: S603 — our own script, from the pack folder
        [sys.executable, "-I", str(target)],
        check=True,
        cwd=target.parent,
        capture_output=True,
        text=True,
    )
    svg = target.with_suffix(".svg")
    if not svg.is_file():
        raise FileNotFoundError(f"{script.name} wrote no {svg.name}")
    svg.write_text(stabilize(svg.read_text(encoding="utf-8")), encoding="utf-8")
    return svg


def check(script: Path) -> str | None:
    """None when the committed SVG is what the script draws; otherwise why not."""
    committed = script.with_suffix(".svg")
    if not committed.is_file():
        return f"{committed.name} is missing: run `make figures`"
    with tempfile.TemporaryDirectory() as scratch:
        fresh = render(script, into=Path(scratch)).read_text(encoding="utf-8")
    if fresh != stabilize(committed.read_text(encoding="utf-8")):
        return f"{committed.name} is not what {script.name} draws: run `make figures`"
    return None


def _validate_packs(scripts: list[Path]) -> int:
    """The packs whose figures were drawn must still validate: the sanitizer runs here."""
    failures = 0
    for pack_dir in sorted({script.parent.parent for script in scripts}):
        try:
            report = validate_pack(load_pack_file(pack_dir / "pack.json"))
        except IstariError as exc:
            print(f"{pack_dir.name}: {exc}", file=sys.stderr)
            failures += 1
            continue
        for issue in report.errors:
            print(f"{pack_dir.name}: {issue.code} {issue.item_key or ''}: {issue.message}")
            failures += 1
    return failures


def cmd_figures(args: argparse.Namespace) -> int:
    scripts = figure_scripts(Path(settings.content_packs_dir), args.pack)
    if not scripts:
        print("no figure scripts found", file=sys.stderr)
        return 1
    failures = 0
    for script in scripts:
        try:
            if args.action == "render":
                svg = render(script)
                print(f"{script.parent.parent.name}/{script.name} -> {svg.name}")
            elif (problem := check(script)) is not None:
                print(f"{script.parent.parent.name}: {problem}")
                failures += 1
            else:
                print(f"{script.parent.parent.name}/{script.name}: up to date")
        except subprocess.CalledProcessError as exc:
            print(f"{script}: exit {exc.returncode}\n{exc.stderr}", file=sys.stderr)
            failures += 1
        except FileNotFoundError as exc:
            print(f"{script}: {exc}", file=sys.stderr)
            failures += 1
    if args.action == "render":
        failures += _validate_packs(scripts)
    return 1 if failures else 0


def register(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    p = sub.add_parser("figures", help="render or check the packs' figure drawings")
    p.add_argument("action", choices=["render", "check"])
    p.add_argument("--pack", default=None, help="one pack's slug; default: every pack")
    p.set_defaults(fn=cmd_figures)
