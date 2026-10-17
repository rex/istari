"""The LocalEmu adapter without a network: the registry, run names, the endpoint guard, and
the S3 versioning scenario end to end on moto."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator

import pytest
import pytest_asyncio
from moto import mock_aws

from app.adapters.localemu import Aws, LocalEmuClient, LocalEmuTimeouts
from app.adapters.localemu.aws import emulator_endpoint
from app.adapters.localemu.scenario import Scenario, ScenarioContext, ScenarioRegistry, SetupFn
from app.adapters.localemu.scenarios import REGISTRY
from app.domain.content.validate import parse_pack
from app.domain.exceptions import UpstreamError
from app.domain.verifier import CheckResult
from tests.fixtures import mini_pack
from tests.localemu_stub import EmulatorState, moto_aws, stub_localemu

SCENARIO = "s3-versioning"


@pytest.fixture
def aws() -> Iterator[Aws]:
    with mock_aws():
        yield moto_aws()


@pytest_asyncio.fixture
async def client(aws: Aws) -> AsyncIterator[LocalEmuClient]:
    emulator = stub_localemu(EmulatorState(), aws)
    yield emulator
    await emulator.aclose()


def _buckets(aws: Aws) -> list[str]:
    return sorted(b.get("Name", "") for b in aws.s3().list_buckets().get("Buckets", []))


def _scenario(scenario_id: str, *, setup: SetupFn) -> Scenario:
    return Scenario(
        id=scenario_id,
        profile="test",
        title="t",
        context="",
        task="",
        setup=setup,
        check=lambda _aws, _ctx: CheckResult(passed=True),
        teardown=lambda _aws, _ctx: None,
        solve=lambda _aws, _ctx: None,
    )


def test_a_pack_lab_names_a_localemu_scenario_family_and_id() -> None:
    pack = mini_pack()
    labs = pack["labs"]
    assert isinstance(labs, list)
    labs[1]["verifier"] = {"backend": "localemu", "profile": "saa", "question": SCENARIO}
    verified = next(lab for lab in parse_pack(pack).labs if lab.slug == "lab-verified")
    assert verified.verifier is not None
    assert (verified.verifier.backend, verified.verifier.profile) == ("localemu", "saa")
    assert verified.verifier.question == SCENARIO


def test_the_registry_groups_scenarios_by_family_and_refuses_twins() -> None:
    assert REGISTRY.profiles == ("saa",)
    assert REGISTRY.ids == (
        "iam-least-privilege",
        "s3-lifecycle",
        SCENARIO,
        "sns-sqs-fanout",
        "vpc-public-private",
    )
    assert [s.id for s in REGISTRY.for_profile("saa")] == list(REGISTRY.ids)
    assert REGISTRY.get(SCENARIO) is not None and REGISTRY.get("nope") is None
    assert REGISTRY.for_profile("cka") == []
    twin = _scenario("twin", setup=lambda _aws, _ctx: "")
    with pytest.raises(ValueError, match="share the id 'twin'"):
        ScenarioRegistry([twin, twin])


def test_every_run_is_named_under_its_scenario_prefix() -> None:
    ctx = ScenarioContext(scenario=SCENARIO, run="a1b2c3", region="us-east-1")
    assert ctx.scenario_prefix == "istari-s3-versioning-"
    assert ctx.prefix == "istari-s3-versioning-a1b2c3"


def test_only_an_emulator_endpoint_is_accepted() -> None:
    assert emulator_endpoint("https://localemu.thelab.host/") == "https://localemu.thelab.host"
    for real in ("https://s3.us-east-1.amazonaws.com", "https://sts.amazonaws.com"):
        with pytest.raises(ValueError, match="real AWS endpoint"):
            LocalEmuClient(real)
    with pytest.raises(ValueError, match="has no host"):
        emulator_endpoint("localemu")


async def test_questions_are_the_registry_s_scenarios(client: LocalEmuClient) -> None:
    questions = await client.questions("saa")
    assert tuple(q.id for q in questions) == REGISTRY.ids
    question = next(q for q in questions if q.id == SCENARIO)
    assert question.title.startswith("Turn on versioning")
    assert "istari-s3-versioning-" in question.context and question.description and question.hint
    assert await client.question("saa", SCENARIO) == question
    assert await client.question("cka", SCENARIO) is None
    assert await client.question("saa", "nope") is None


async def test_versioning_fails_until_it_is_on_then_passes(
    client: LocalEmuClient, aws: Aws
) -> None:
    run = (await client.ensure_session("saa")).id
    setup = await client.setup(SCENARIO, run=run)
    bucket = f"istari-s3-versioning-{run}"
    assert setup.ok and bucket in setup.output and _buckets(aws) == [bucket]

    failed = await client.check(SCENARIO, run=run)
    assert failed.passed is False and failed.reason_line == "FAIL: versioning is off"

    aws.s3().put_bucket_versioning(Bucket=bucket, VersioningConfiguration={"Status": "Enabled"})
    passed = await client.check(SCENARIO, run=run)
    assert passed.passed is True and passed.reason_line == "PASS: versioning is on"


async def test_a_fresh_setup_clears_earlier_runs_and_teardown_clears_all(
    client: LocalEmuClient, aws: Aws
) -> None:
    aws.s3().create_bucket(Bucket="someone-elses-bucket")
    await client.setup(SCENARIO, run="aaaaaa")
    s3 = aws.s3()
    s3.put_bucket_versioning(
        Bucket="istari-s3-versioning-aaaaaa", VersioningConfiguration={"Status": "Enabled"}
    )
    s3.put_object(Bucket="istari-s3-versioning-aaaaaa", Key="note.txt", Body=b"one")
    s3.put_object(Bucket="istari-s3-versioning-aaaaaa", Key="note.txt", Body=b"two")
    await client.setup(SCENARIO, run="bbbbbb")
    assert _buckets(aws) == ["istari-s3-versioning-bbbbbb", "someone-elses-bucket"]
    await client.teardown(SCENARIO)
    assert _buckets(aws) == ["someone-elses-bucket"]


async def test_nothing_to_grade_is_ungradable_not_a_failure(
    client: LocalEmuClient, aws: Aws
) -> None:
    never = await client.check(SCENARIO, run="")
    assert never.passed is False and never.output == ""
    assert never.unavailable_reason == "Set the lab up first; there is nothing to check."
    await client.setup(SCENARIO, run="cccccc")
    aws.s3().delete_bucket(Bucket="istari-s3-versioning-cccccc")
    gone = await client.check(SCENARIO, run="cccccc")
    assert gone.passed is False and gone.output == ""
    assert (
        gone.unavailable_reason
        == "Bucket istari-s3-versioning-cccccc is gone; set the lab up again."
    )
    with pytest.raises(ValueError, match="run id"):
        await client.setup(SCENARIO, run="")


async def test_emulator_refusals_are_upstream_errors_and_bugs_stay_bugs(aws: Aws) -> None:
    def refused(aws: Aws, ctx: ScenarioContext) -> str:
        aws.s3().get_bucket_versioning(Bucket=ctx.prefix)
        return ""

    def buggy(_aws: Aws, _ctx: ScenarioContext) -> str:
        raise KeyError("a bug in the scenario, not the emulator's doing")

    registry = ScenarioRegistry(
        [_scenario("refused", setup=refused), _scenario("buggy", setup=buggy)]
    )
    client = LocalEmuClient("http://localemu.test:4566", aws=aws, scenarios=registry)
    with pytest.raises(UpstreamError) as exc:
        await client.setup("refused", run="dddddd")
    assert "refused setting up refused: NoSuchBucket" in exc.value.message
    assert exc.value.details == {"code": "NoSuchBucket", "step": "setting up refused"}
    with pytest.raises(KeyError):
        await client.setup("buggy", run="dddddd")
    with pytest.raises(UpstreamError, match="no scenario 'ghost'"):
        await client.setup("ghost", run="dddddd")


async def test_an_unreachable_emulator_is_an_upstream_error() -> None:
    client = LocalEmuClient(
        "http://127.0.0.1:9", timeouts=LocalEmuTimeouts(connect=1.0, api=1.0, attempts=1)
    )
    try:
        with pytest.raises(UpstreamError) as exc:
            await client.setup(SCENARIO, run="eeeeee")
        assert exc.value.message.startswith("LocalEmu at http://127.0.0.1:9 is not reachable")
        assert exc.value.status == 502
    finally:
        await client.aclose()
