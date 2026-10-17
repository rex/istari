"""The three labs of rex/istari#88 on moto, clause by clause: least-privilege IAM, a public and
private VPC, SNS to SQS fan-out. Each wrong answer fails on the clause that names it, and
teardown leaves nothing behind. Then the IAM evaluator's own rules."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Iterator
from typing import Any

import pytest
import pytest_asyncio
from moto import mock_aws

from app.adapters.localemu import Aws, LocalEmuClient
from app.adapters.localemu.scenarios.iam_eval import allowed, statements
from tests.localemu_stub import EmulatorState, moto_aws, stub_localemu

RUN = "beef01"


@pytest.fixture
def aws() -> Iterator[Aws]:
    with mock_aws():
        yield moto_aws()


@pytest_asyncio.fixture
async def client(aws: Aws) -> AsyncIterator[LocalEmuClient]:
    emulator = stub_localemu(EmulatorState(), aws)
    yield emulator
    await emulator.aclose()


def _policy(*statement: dict[str, Any]) -> str:
    return json.dumps({"Version": "2012-10-17", "Statement": list(statement)})


# ── iam-least-privilege ───────────────────────────────────────────────────
IAM = "iam-least-privilege"
BUCKET = f"istari-{IAM}-{RUN}"
ANALYST = f"{BUCKET}-analyst"


def _allow(action: object, resource: object) -> dict[str, Any]:
    return {"Effect": "Allow", "Action": action, "Resource": resource}


@pytest.mark.parametrize(
    ("policy", "verdict"),
    [
        (None, f"FAIL: the analyst must be able to s3:GetObject on {BUCKET}/reports/*"),
        (
            _policy(_allow("s3:*", f"arn:aws:s3:::{BUCKET}/*")),
            "FAIL: the analyst can read payroll/: narrow the Resource to the reports/ prefix",
        ),
        (
            _policy(_allow(["s3:GetObject", "s3:PutObject"], f"arn:aws:s3:::{BUCKET}/reports/*")),
            "FAIL: the analyst can write to reports/: allow s3:GetObject and nothing more",
        ),
        (
            _policy(_allow("s3:GetObject", "arn:aws:s3:::*/reports/*")),
            "FAIL: the analyst can read other buckets: name this bucket in the Resource",
        ),
        (
            _policy(
                _allow("s3:GetObject", f"arn:aws:s3:::{BUCKET}/*"),
                {
                    "Effect": "Deny",
                    "Action": "s3:*",
                    "Resource": f"arn:aws:s3:::{BUCKET}/payroll/*",
                },
            ),
            "PASS: the analyst reads reports/ and nothing else",
        ),
    ],
)
async def test_least_privilege_names_what_the_policy_gives_away(
    client: LocalEmuClient, aws: Aws, policy: str | None, verdict: str
) -> None:
    await client.setup(IAM, run=RUN)
    if policy is not None:
        aws.iam().put_user_policy(UserName=ANALYST, PolicyName="p", PolicyDocument=policy)
    result = await client.check(IAM, run=RUN)
    assert result.reason_line == verdict
    assert result.passed is verdict.startswith("PASS")


async def test_least_privilege_reads_managed_and_group_policies(
    client: LocalEmuClient, aws: Aws
) -> None:
    setup = await client.setup(IAM, run=RUN)
    assert ANALYST in setup.output and "access key id is" in setup.output
    iam = aws.iam()
    # A managed policy shaped like AWS's AmazonS3ReadOnlyAccess (moto ships none of AWS's).
    read_only = iam.create_policy(
        PolicyName=f"{BUCKET}-read-only",
        PolicyDocument=_policy(_allow(["s3:Get*", "s3:List*"], "*")),
    )["Policy"]["Arn"]
    iam.attach_user_policy(UserName=ANALYST, PolicyArn=read_only)
    broad = await client.check(IAM, run=RUN)
    assert broad.reason_line.startswith("FAIL: the analyst can read payroll/")
    iam.detach_user_policy(UserName=ANALYST, PolicyArn=read_only)
    group = f"istari-{IAM}-{RUN}-readers"
    iam.create_group(GroupName=group)
    iam.put_group_policy(
        GroupName=group,
        PolicyName="reports",
        PolicyDocument=_policy(_allow("s3:GetObject", f"arn:aws:s3:::{BUCKET}/reports/*")),
    )
    iam.add_user_to_group(GroupName=group, UserName=ANALYST)
    assert (await client.check(IAM, run=RUN)).passed is True
    await client.teardown(IAM)
    assert iam.list_users()["Users"] == [] and iam.list_groups()["Groups"] == []
    assert iam.list_policies(Scope="Local")["Policies"] == []


async def test_conditional_statements_are_named_not_guessed(
    client: LocalEmuClient, aws: Aws
) -> None:
    await client.setup(IAM, run=RUN)
    conditional = _allow("s3:GetObject", f"arn:aws:s3:::{BUCKET}/reports/*")
    conditional.update(Sid="OnlyFromHome", Condition={"IpAddress": {"aws:SourceIp": "10.0.0.0/8"}})
    aws.iam().put_user_policy(UserName=ANALYST, PolicyName="p", PolicyDocument=_policy(conditional))
    result = await client.check(IAM, run=RUN)
    assert "not evaluated (they carry a Condition): OnlyFromHome" in result.output
    assert result.passed is False


def test_the_evaluator_follows_iam_s_rules() -> None:
    granted, skipped = statements(
        {
            "Statement": [
                {"Effect": "Allow", "NotAction": "s3:Delete*", "Resource": "arn:aws:s3:::b/*"},
                {"Effect": "Deny", "Action": "S3:GETOBJECT", "Resource": "arn:aws:s3:::b/secret?"},
            ]
        }
    )
    assert skipped == []
    assert allowed(granted, "s3:GetObject", "arn:aws:s3:::b/report")
    assert not allowed(granted, "s3:DeleteObject", "arn:aws:s3:::b/report")
    assert not allowed(granted, "s3:GetObject", "arn:aws:s3:::b/secret1")
    assert not allowed(granted, "s3:GetObject", "arn:aws:s3:::other/report")
    assert statements(
        json.dumps({"Statement": {"Effect": "Allow", "Action": "*", "Resource": "*"}})
    )[0][0].actions == ("*",)


# ── vpc-public-private ────────────────────────────────────────────────────
VPC = "vpc-public-private"


def _vpc(aws: Aws) -> str:
    vpcs = aws.ec2().describe_vpcs(
        Filters=[{"Name": "tag:Name", "Values": [f"istari-{VPC}-{RUN}"]}]
    )
    return vpcs["Vpcs"][0]["VpcId"]


def _route(aws: Aws, vpc: str, subnet: str, **target: str) -> None:
    ec2 = aws.ec2()
    table = ec2.create_route_table(VpcId=vpc)["RouteTable"]["RouteTableId"]
    ec2.create_route(RouteTableId=table, DestinationCidrBlock="0.0.0.0/0", **target)  # type: ignore[arg-type]
    ec2.associate_route_table(RouteTableId=table, SubnetId=subnet)


async def test_the_vpc_check_wants_the_nat_in_the_public_subnet(
    client: LocalEmuClient, aws: Aws
) -> None:
    await client.setup(VPC, run=RUN)
    ec2, vpc = aws.ec2(), _vpc(aws)
    public = ec2.create_subnet(VpcId=vpc, CidrBlock="10.0.1.0/24")["Subnet"]["SubnetId"]
    private = ec2.create_subnet(VpcId=vpc, CidrBlock="10.0.2.0/24")["Subnet"]["SubnetId"]
    igw = ec2.create_internet_gateway()["InternetGateway"]["InternetGatewayId"]
    ec2.attach_internet_gateway(InternetGatewayId=igw, VpcId=vpc)
    _route(aws, vpc, public, GatewayId=igw)
    no_nat = await client.check(VPC, run=RUN)
    assert no_nat.reason_line.startswith("FAIL: put a NAT gateway in the public subnet")
    # A NAT gateway in the private subnet cannot reach the internet: still the same clause.
    eip = ec2.allocate_address(Domain="vpc")["AllocationId"]
    wrong = ec2.create_nat_gateway(SubnetId=private, AllocationId=eip)["NatGateway"]
    _route(aws, vpc, private, NatGatewayId=wrong["NatGatewayId"])
    misplaced = await client.check(VPC, run=RUN)
    assert misplaced.reason_line.startswith("FAIL: put a NAT gateway in the public subnet")
    assert "[ok] private subnet" in misplaced.output
    await client.teardown(VPC)
    assert aws.ec2().describe_vpcs(Filters=[{"Name": "tag-key", "Values": ["Name"]}])["Vpcs"] == []


# ── sns-sqs-fanout ────────────────────────────────────────────────────────
FANOUT = "sns-sqs-fanout"
PREFIX = f"istari-{FANOUT}-{RUN}"


def _subscribe(aws: Aws, role: str, policy: dict[str, Any] | None) -> None:
    sqs, sns = aws.sqs(), aws.sns()
    topic = next(
        t["TopicArn"] for t in sns.list_topics()["Topics"] if t["TopicArn"].endswith("-orders")
    )
    url = sqs.create_queue(QueueName=f"{PREFIX}-{role}")["QueueUrl"]
    arn = sqs.get_queue_attributes(QueueUrl=url, AttributeNames=["QueueArn"])["Attributes"][
        "QueueArn"
    ]
    if policy is not None:
        statement = {**policy, "Resource": arn}
        if "Condition" in statement:
            statement["Condition"] = {"ArnEquals": {"aws:SourceArn": topic}}
        sqs.set_queue_attributes(QueueUrl=url, Attributes={"Policy": _policy(statement)})
    sns.subscribe(TopicArn=topic, Protocol="sqs", Endpoint=arn)


SNS_SEND = {
    "Effect": "Allow",
    "Principal": {"Service": "sns.amazonaws.com"},
    "Action": "sqs:SendMessage",
}


@pytest.mark.parametrize(
    ("queues", "verdict"),
    [
        ([], "FAIL: subscribe two queues to the topic (0 so far)"),
        ([("billing", None), ("shipping", None)], "FAIL: queue policy must allow"),
        (
            [("billing", SNS_SEND), ("shipping", SNS_SEND)],
            "FAIL: scope each queue policy to the topic with an aws:SourceArn condition: "
            f"{PREFIX}-billing, {PREFIX}-shipping",
        ),
        (
            [
                ("billing", {**SNS_SEND, "Condition": True}),
                ("shipping", {**SNS_SEND, "Condition": True}),
            ],
            "PASS: one order event fans out to every queue",
        ),
    ],
)
async def test_fanout_wants_two_scoped_queues_that_both_receive(
    client: LocalEmuClient, aws: Aws, queues: list[tuple[str, dict[str, Any] | None]], verdict: str
) -> None:
    await client.setup(FANOUT, run=RUN)
    for role, policy in queues:
        _subscribe(aws, role, policy)
    result = await client.check(FANOUT, run=RUN)
    assert result.reason_line.startswith(verdict)
    if queues:
        assert "[ok] one published message reached every subscribed queue" in result.output
    await client.teardown(FANOUT)
    assert aws.sqs().list_queues(QueueNamePrefix=f"istari-{FANOUT}-").get("QueueUrls", []) == []
    assert aws.sns().list_topics()["Topics"] == []
