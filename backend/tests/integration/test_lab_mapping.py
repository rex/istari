"""`labs check-map` against the stub: the shipped CKA pack maps when the instance serves its
ids, the report names exactly what is missing when it does not, and a silent instance is a
distinct exit code."""

from __future__ import annotations

import json
from pathlib import Path

from app.adapters.k16s import K16sClient
from app.cli.labs_cmds import check_map, verified_labs
from app.domain.content.validate import parse_pack
from tests.k16s_stub import StubState, placeholder_bank

PACK_PATH = Path(__file__).resolve().parents[3] / "content" / "packs" / "k8s-cka-k16s" / "pack.json"


def _mapped(profile: str | None = None) -> dict[str, dict[str, int]]:
    spec = parse_pack(json.loads(PACK_PATH.read_text(encoding="utf-8")))
    return verified_labs([spec], profile)


async def test_check_map_passes_when_the_instance_serves_every_id(
    stub_k16s: K16sClient, stub: StubState
) -> None:
    mapped = _mapped()
    stub.questions = placeholder_bank({p: sorted(ids) for p, ids in mapped.items()})
    lines: list[str] = []
    assert await check_map(stub_k16s, mapped, lines.append) == 0
    assert lines[0] == "cka: 18 labs, 18 questions served"
    assert lines[1].startswith("  all mapped")
    assert any(line.startswith("cka2: 18 labs, 18 questions served") for line in lines)
    # The placeholder bank weighs everything 4; the pack differs, so drift is a note, not a fail.
    assert any(line.startswith("  weight drift: 01-fix-notready-node is 7") for line in lines)
    assert not any("missing" in line or "unmapped" in line for line in lines)


async def test_check_map_names_the_missing_ids(stub_k16s: K16sClient) -> None:
    # The stub's own bank serves three ids of its own, none of which the pack maps.
    lines: list[str] = []
    assert await check_map(stub_k16s, _mapped("cka"), lines.append) == 1
    assert lines[0] == "cka: 18 labs, 2 questions served"
    assert lines[1].startswith("  missing (no such question on the instance): 01-fix-notready-node")
    assert any("unmapped" in line and "stub-01-crashloop" in line for line in lines)
    assert not any(line.startswith("cka2:") for line in lines)


async def test_check_map_reports_an_instance_that_does_not_answer() -> None:
    client = K16sClient("http://127.0.0.1:9")
    lines: list[str] = []
    try:
        assert await check_map(client, _mapped("cka2"), lines.append) == 2
    finally:
        await client.aclose()
    assert len(lines) == 1
    assert lines[0].startswith("cka2: K16S at http://127.0.0.1:9 is not reachable")
    assert await check_map(client, {}, lines.append) == 0
    assert lines[-1] == "no verified labs found in the packs"
