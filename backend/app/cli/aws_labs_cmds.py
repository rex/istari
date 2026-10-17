"""`labs aws-check`: every LocalEmu scenario run end to end against the real emulator.

    uv run python -m app.cli labs aws-check                       # LOCALEMU_BASE_URL
    uv run python -m app.cli labs aws-check --scenario s3-lifecycle --base-url http://localemu.lan:4566

Per scenario: setup, check (must fail, since the task is not done yet), solve by API, check
(must pass), teardown. Then every pack lab with a `localemu` verifier must name a registered
scenario. Exit 0 when all of that holds; 1 when a scenario misbehaves or a lab names a missing
scenario; 2 when no emulator is configured or it does not answer. Not a gate: it needs the
emulator. It tears down what it makes and records nothing in Istari.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Callable
from pathlib import Path

from app.adapters.localemu import LocalEmuClient
from app.config import settings
from app.domain.content.load import load_pack_file
from app.domain.content.schemas.pack import ContentPackSpec
from app.domain.exceptions import UpstreamError

Emit = Callable[[str], None]
OK, BROKEN, DOWN = 0, 1, 2


def localemu_labs(packs: list[ContentPackSpec]) -> dict[str, str]:
    """Lab slug -> scenario id, over every lab whose verifier is `localemu`."""
    return {
        lab.slug: lab.verifier.question
        for pack in packs
        for lab in pack.labs
        if lab.verifier is not None and lab.verifier.backend == "localemu"
    }


async def run_scenario(client: LocalEmuClient, scenario_id: str, emit: Emit) -> int:
    """One scenario's whole loop; OK, BROKEN (it misgraded) or DOWN (the emulator failed)."""
    scenario = client.scenarios.get(scenario_id)
    if scenario is None:
        emit(f"{scenario_id}: no such scenario")
        return BROKEN
    run = (await client.ensure_session(scenario.profile)).id
    try:
        await client.setup(scenario_id, run=run)
        unsolved = await client.check(scenario_id, run=run)
        if unsolved.passed or unsolved.unavailable_reason:
            said = unsolved.unavailable_reason or unsolved.reason_line
            emit(f"{scenario_id}: the unsolved run did not fail ({said})")
            return BROKEN
        await client.solve(scenario_id, run=run)
        solved = await client.check(scenario_id, run=run)
        if not solved.passed:
            said = solved.unavailable_reason or solved.reason_line
            emit(f"{scenario_id}: the solved run did not pass ({said})")
            return BROKEN
        emit(f"{scenario_id}: unsolved fails ({unsolved.reason_line}); solved passes")
        return OK
    except UpstreamError as exc:
        emit(f"{scenario_id}: {exc.message}")
        return DOWN
    finally:
        try:
            await client.teardown(scenario_id)
        except UpstreamError as exc:
            emit(f"{scenario_id}: teardown failed: {exc.message}")


async def aws_check(
    client: LocalEmuClient, scenario_ids: list[str], labs: dict[str, str], emit: Emit
) -> int:
    try:
        status = await client.status()
    except UpstreamError as exc:
        emit(exc.message)
        return DOWN
    emit(f"LocalEmu at {client.base_url}: {status.mode}")
    code = OK
    for scenario_id in scenario_ids:
        code = max(code, await run_scenario(client, scenario_id, emit))
    missing = sorted(slug for slug, sid in labs.items() if client.scenarios.get(sid) is None)
    for slug in missing:
        emit(f"lab {slug}: names scenario '{labs[slug]}', which this build does not have")
        code = max(code, BROKEN)
    unmapped = sorted(set(client.scenarios.ids) - set(labs.values()))
    if unmapped:
        emit("scenarios no lab uses yet: " + ", ".join(unmapped))
    return code


def cmd_aws_check(args: argparse.Namespace) -> int:
    base_url = args.base_url or settings.localemu_base_url
    if not base_url:
        print("no emulator configured: set LOCALEMU_BASE_URL or pass --base-url", file=sys.stderr)
        return DOWN
    paths = [Path(p) for p in args.pack] or sorted(
        Path(settings.content_packs_dir).glob("*/pack.json")
    )
    labs = localemu_labs([load_pack_file(path) for path in paths])

    async def go() -> int:
        client = LocalEmuClient(base_url, region=settings.localemu_region)
        scenario_ids = args.scenario or list(client.scenarios.ids)
        try:
            return await aws_check(client, scenario_ids, labs, print)
        finally:
            await client.aclose()

    return asyncio.run(go())


def add_parser(labs_sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    p = labs_sub.add_parser(
        "aws-check", help="run every LocalEmu scenario end to end against the emulator"
    )
    p.add_argument("--scenario", action="append", default=[], help="only this one; repeatable")
    p.add_argument(
        "--pack",
        action="append",
        default=[],
        help="a pack file; repeatable. Default: every content/packs/*/pack.json",
    )
    p.add_argument("--base-url", default=None, help="the emulator; default LOCALEMU_BASE_URL")
    p.set_defaults(fn=cmd_aws_check)
