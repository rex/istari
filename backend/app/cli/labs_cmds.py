"""`labs check-map`: every verified lab's question id against what the K16S instance serves.

    uv run python -m app.cli labs check-map                  # every pack under content/packs
    uv run python -m app.cli labs check-map --pack ../content/packs/k8s-cka-k16s/pack.json
    uv run python -m app.cli labs check-map --profile cka --base-url http://k16s.lan:8080

Reads the pack files, not the database, so it runs anywhere the packs are. Exit 0 when the
instance serves every mapped question; 1 when one is missing (that lab would fail at setup);
2 when no backend is configured or the instance does not answer. Served questions no lab
covers and weights that drifted since the pack was written are notes, never failures.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Callable
from pathlib import Path

from app.adapters.k16s import K16sClient
from app.config import settings
from app.domain.content.load import load_pack_file
from app.domain.content.schemas.pack import ContentPackSpec
from app.domain.exceptions import UpstreamError
from app.domain.verifier_mapping import MappingReport, compare_mapping

Emit = Callable[[str], None]


def verified_labs(
    packs: list[ContentPackSpec], profile: str | None = None
) -> dict[str, dict[str, int]]:
    """profile -> {question id: weight} over every lab with a K16S verifier."""
    mapped: dict[str, dict[str, int]] = {}
    for pack in packs:
        for lab in pack.labs:
            spec = lab.verifier
            if spec is None or spec.backend != "k16s":
                continue
            if profile is not None and spec.profile != profile:
                continue
            mapped.setdefault(spec.profile, {})[spec.question] = spec.weight
    return mapped


def render(report: MappingReport) -> list[str]:
    """The report as the operator reads it: one line per profile, then the notes."""
    lines = [f"{report.profile}: {report.lab_count} labs, {report.question_count} questions served"]
    if report.ok:
        lines.append("  all mapped: every lab's question is served")
    else:
        missing = ", ".join(report.missing_questions)
        lines.append(f"  missing (no such question on the instance): {missing}")
    if report.unmapped_questions:
        lines.append("  unmapped (served, no lab yet): " + ", ".join(report.unmapped_questions))
    for drift in report.weight_drift:
        lines.append(
            f"  weight drift: {drift.question} is {drift.pack_weight} in the pack, "
            f"{drift.served_weight} on the instance"
        )
    if report.heavy_questions:
        lines.append("  full install only: " + ", ".join(report.heavy_questions))
    return lines


async def check_map(client: K16sClient, mapped: dict[str, dict[str, int]], emit: Emit) -> int:
    """Compare each profile; 0 when every lab maps, 1 when any is missing, 2 on no answer."""
    if not mapped:
        emit("no verified labs found in the packs")
        return 0
    code = 0
    for profile, weights in sorted(mapped.items()):
        try:
            served = await client.questions(profile)
        except UpstreamError as exc:
            emit(f"{profile}: {exc.message}")
            code = 2
            continue
        report = compare_mapping(profile, list(weights), served, lab_weights=weights)
        for line in render(report):
            emit(line)
        if not report.ok:
            code = max(code, 1)
    return code


def _load_packs(paths: list[Path]) -> list[ContentPackSpec]:
    return [load_pack_file(path) for path in paths]


def cmd_check_map(args: argparse.Namespace) -> int:
    paths = [Path(p) for p in args.pack] or sorted(
        Path(settings.content_packs_dir).glob("*/pack.json")
    )
    if not paths:
        print("no packs found", file=sys.stderr)
        return 2
    base_url = args.base_url or settings.k16s_base_url
    if not base_url:
        print("no K16S configured: set K16S_BASE_URL or pass --base-url", file=sys.stderr)
        return 2
    mapped = verified_labs(_load_packs(paths), args.profile)

    async def go() -> int:
        client = K16sClient(base_url)
        try:
            return await check_map(client, mapped, print)
        finally:
            await client.aclose()

    return asyncio.run(go())


def register(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    labs = sub.add_parser("labs", help="verified labs and their backend")
    labs_sub = labs.add_subparsers(dest="labs_command", required=True)
    p = labs_sub.add_parser(
        "check-map", help="compare the packs' question ids with what the K16S instance serves"
    )
    p.add_argument(
        "--pack",
        action="append",
        default=[],
        help="a pack file; repeatable. Default: every content/packs/*/pack.json",
    )
    p.add_argument("--profile", default=None, help="only this K16S profile")
    p.add_argument("--base-url", default=None, help="the instance; default K16S_BASE_URL")
    p.set_defaults(fn=cmd_check_map)
