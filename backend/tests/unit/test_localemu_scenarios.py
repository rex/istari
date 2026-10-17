"""Every LocalEmu scenario on moto: unsolved fails, solved passes, teardown clears it. Then the
lifecycle check clause by clause, and the loop `make aws-labs-check` runs."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from moto import mock_aws

from app.adapters.localemu import Aws, LocalEmuClient
from app.adapters.localemu.scenario import Scenario, ScenarioRegistry
from app.adapters.localemu.scenarios import REGISTRY
from app.cli.aws_labs_cmds import aws_check, localemu_labs, run_scenario
from app.domain.content.load import load_pack_file
from app.domain.verifier import CheckResult
from tests.localemu_stub import EmulatorState, moto_aws, stub_localemu

PACKS = Path(__file__).resolve().parents[3] / "content" / "packs"
LIFECYCLE = "s3-lifecycle"
RUN = "f00d01"
BUCKET = f"istari-{LIFECYCLE}-{RUN}"


@pytest.fixture
def aws() -> Iterator[Aws]:
    with mock_aws():
        yield moto_aws()


@pytest_asyncio.fixture
async def client(aws: Aws) -> AsyncIterator[LocalEmuClient]:
    emulator = stub_localemu(EmulatorState(), aws)
    yield emulator
    await emulator.aclose()


def _buckets(aws: Aws, prefix: str) -> list[str]:
    names = (b.get("Name", "") for b in aws.s3().list_buckets().get("Buckets", []))
    return sorted(name for name in names if name.startswith(prefix))


@pytest.mark.parametrize("scenario_id", REGISTRY.ids)
async def test_every_scenario_fails_unsolved_passes_solved_and_tears_down(
    client: LocalEmuClient, aws: Aws, scenario_id: str
) -> None:
    setup = await client.setup(scenario_id, run=RUN)
    assert setup.ok and f"istari-{scenario_id}-{RUN}" in setup.output
    unsolved = await client.check(scenario_id, run=RUN)
    assert unsolved.passed is False and unsolved.unavailable_reason is None
    assert unsolved.reason_line.startswith("FAIL: ")
    await client.solve(scenario_id, run=RUN)
    solved = await client.check(scenario_id, run=RUN)
    assert solved.passed is True and solved.reason_line.startswith("PASS: ")
    await client.teardown(scenario_id)
    assert _buckets(aws, f"istari-{scenario_id}-") == []


# ── The lifecycle check, clause by clause ─────────────────────────────────
def _rule(**over: Any) -> dict[str, Any]:
    rule: dict[str, Any] = {
        "ID": "logs",
        "Filter": {"Prefix": "logs/"},
        "Status": "Enabled",
        "Transitions": [{"Days": 30, "StorageClass": "GLACIER"}],
        "Expiration": {"Days": 365},
    }
    rule.update(over)
    return rule


NO_LOGS_RULE = "FAIL: no enabled rule is scoped to exactly logs/ (no tag or size filter)"


@pytest.mark.parametrize(
    ("rules", "verdict"),
    [
        ([], NO_LOGS_RULE),
        ([_rule(Status="Disabled")], NO_LOGS_RULE),
        ([_rule(Filter={"Prefix": ""})], NO_LOGS_RULE),
        (
            [_rule(Filter={"And": {"Prefix": "logs/", "Tags": [{"Key": "k", "Value": "v"}]}})],
            NO_LOGS_RULE,
        ),
        (
            [_rule(Transitions=[{"Days": 30, "StorageClass": "STANDARD_IA"}])],
            "FAIL: logs/ must move to GLACIER 30 days after creation "
            "(found: STANDARD_IA at 30 days)",
        ),
        ([_rule(Expiration={"Days": 90})], "FAIL: logs/ must expire 365 days after creation"),
        (
            [_rule(), _rule(ID="sweep", Filter={"Prefix": ""}, Transitions=[])],
            "FAIL: rule sweep also acts on reports/q3-costs.csv",
        ),
        ([_rule()], "PASS: logs/ archives at 30 days and expires at 365"),
        (
            [_rule(ID="archive", Expiration=None), _rule(ID="expire", Transitions=[])],
            "PASS: logs/ archives at 30 days and expires at 365",
        ),
    ],
)
async def test_the_lifecycle_check_grades_each_clause(
    client: LocalEmuClient, aws: Aws, rules: list[dict[str, Any]], verdict: str
) -> None:
    await client.setup(LIFECYCLE, run=RUN)
    cleaned = [{k: v for k, v in r.items() if v not in (None, [])} for r in rules]
    if cleaned:
        aws.s3().put_bucket_lifecycle_configuration(
            Bucket=BUCKET,
            LifecycleConfiguration={"Rules": cleaned},  # type: ignore[typeddict-item]
        )
    result = await client.check(LIFECYCLE, run=RUN)
    assert result.reason_line == verdict
    assert result.passed is verdict.startswith("PASS")
    assert result.output.splitlines()[0].startswith(f"Bucket {BUCKET}: {len(rules)} lifecycle")


async def test_the_lifecycle_check_lists_every_clause(client: LocalEmuClient) -> None:
    await client.setup(LIFECYCLE, run=RUN)
    lines = (await client.check(LIFECYCLE, run=RUN)).output.splitlines()
    assert lines[1:5] == [
        "[--] no enabled rule is scoped to exactly logs/ (no tag or size filter)",
        "[--] logs/ must move to GLACIER 30 days after creation",
        "[--] logs/ must expire 365 days after creation",
        "[ok] reports/ is left alone",
    ]


# ── `make aws-labs-check` ─────────────────────────────────────────────────
def test_every_pack_lab_names_a_registered_scenario() -> None:
    labs = localemu_labs([load_pack_file(p) for p in sorted(PACKS.glob("*/pack.json"))])
    assert labs == {"lab-s3-lifecycle": LIFECYCLE}
    assert all(REGISTRY.get(scenario) is not None for scenario in labs.values())


async def test_aws_check_runs_every_scenario_and_maps_the_labs(client: LocalEmuClient) -> None:
    lines: list[str] = []
    code = await aws_check(
        client, list(REGISTRY.ids), {"lab-s3-lifecycle": LIFECYCLE}, lines.append
    )
    assert code == 0, lines
    assert lines[0] == "LocalEmu at http://localemu.test:4566: community 1.2.0"
    assert lines[1] == f"{LIFECYCLE}: unsolved fails ({NO_LOGS_RULE}); solved passes"
    assert lines[2].startswith("s3-versioning: unsolved fails (FAIL: versioning is off)")
    assert lines[-1] == "scenarios no lab uses yet: s3-versioning"


async def test_aws_check_fails_a_lab_whose_scenario_is_missing(client: LocalEmuClient) -> None:
    lines: list[str] = []
    assert await aws_check(client, [], {"lab-ghost": "ghost"}, lines.append) == 1
    assert "lab lab-ghost: names scenario 'ghost', which this build does not have" in lines


async def test_aws_check_stops_when_the_emulator_is_down(aws: Aws) -> None:
    client = stub_localemu(EmulatorState(mode="down"), aws)
    lines: list[str] = []
    try:
        assert await aws_check(client, list(REGISTRY.ids), {}, lines.append) == 2
    finally:
        await client.aclose()
    assert lines == ["LocalEmu at http://localemu.test:4566 is not reachable: connection refused"]


async def test_a_scenario_that_passes_before_it_is_solved_is_broken(aws: Aws) -> None:
    lenient = Scenario(
        id="lenient",
        profile="test",
        title="t",
        context="",
        task="",
        setup=lambda _aws, _ctx: "",
        check=lambda _aws, _ctx: CheckResult(passed=True, output="PASS: anything goes"),
        teardown=lambda _aws, _ctx: None,
        solve=lambda _aws, _ctx: None,
    )
    client = LocalEmuClient(
        "http://localemu.test:4566", aws=aws, scenarios=ScenarioRegistry([lenient])
    )
    lines: list[str] = []
    try:
        assert await run_scenario(client, "lenient", lines.append) == 1
    finally:
        await client.aclose()
    assert lines == ["lenient: the unsolved run did not fail (PASS: anything goes)"]
