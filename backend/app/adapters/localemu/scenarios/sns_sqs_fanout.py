"""SNS to SQS fan-out: one order event, two queues that each get a copy.

Setup makes the topic `<prefix>-orders`. The learner creates two queues (named with the run's
prefix, so the lab can find and clear them), subscribes both to the topic, and gives each a
queue policy that lets SNS send to it, scoped to this topic with `aws:SourceArn`. The check
reads the subscriptions and the queue policies, then publishes one message and polls every
subscribed queue for it, allowing a few seconds for delivery.
"""

from __future__ import annotations

import json
import secrets
import time
from fnmatch import fnmatchcase

from botocore.exceptions import ClientError

from app.adapters.localemu.aws import Aws
from app.adapters.localemu.scenario import Scenario, ScenarioContext
from app.adapters.localemu.scenarios.grading import Clause, gone, verdict
from app.adapters.localemu.scenarios.s3_util import error_code
from app.domain.verifier import CheckResult

SNS_SERVICE = "sns.amazonaws.com"
DELIVERY_SECONDS = 10.0


def _topic_arn(aws: Aws, ctx: ScenarioContext) -> str | None:
    wanted = f"{ctx.prefix}-orders"
    topics = aws.sns().list_topics().get("Topics", [])
    return next(
        (t["TopicArn"] for t in topics if t.get("TopicArn", "").endswith(f":{wanted}")), None
    )


def setup(aws: Aws, ctx: ScenarioContext) -> str:
    arn = aws.sns().create_topic(Name=f"{ctx.prefix}-orders")["TopicArn"]
    return (
        f"Topic {arn} is ready, with no subscribers. Name your queues starting with "
        f"{ctx.prefix}- so the lab can find and clear them."
    )


def _statements(policy: str) -> list[dict[str, object]]:
    try:
        raw = json.loads(policy).get("Statement", [])
    except (ValueError, AttributeError):
        return []
    items = raw if isinstance(raw, list) else [raw]
    return [s for s in items if isinstance(s, dict)]


def _strings(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, dict):
        return [s for v in value.values() for s in _strings(v)]
    return []


def _lets_sns_send(statement: dict[str, object]) -> bool:
    principals = _strings(statement.get("Principal"))
    actions = [a.lower() for a in _strings(statement.get("Action"))]
    return (
        statement.get("Effect") == "Allow"
        and (SNS_SERVICE in principals or "*" in principals)
        and any(fnmatchcase("sqs:sendmessage", a) for a in actions)
    )


def _scoped_to(statement: dict[str, object], topic: str) -> bool:
    condition = statement.get("Condition")
    if not isinstance(condition, dict):
        return False
    for test in condition.values():
        if not isinstance(test, dict):
            continue
        for key, value in test.items():
            if key.lower() == "aws:sourcearn" and any(
                fnmatchcase(topic, v) for v in _strings(value)
            ):
                return True
    return False


def _delivered(aws: Aws, urls: dict[str, str], token: str) -> set[str]:
    """The queues (by name) the token reached within one shared deadline."""
    sqs = aws.sqs()
    reached: set[str] = set()
    deadline = time.monotonic() + DELIVERY_SECONDS
    while time.monotonic() < deadline and reached != set(urls):
        for name in sorted(set(urls) - reached):
            for message in sqs.receive_message(
                QueueUrl=urls[name], MaxNumberOfMessages=10, WaitTimeSeconds=1
            ).get("Messages", []):
                sqs.delete_message(QueueUrl=urls[name], ReceiptHandle=message["ReceiptHandle"])
                if token in message.get("Body", ""):
                    reached.add(name)
    return reached


def _queue(aws: Aws, arn: str) -> tuple[str, list[dict[str, object]]] | None:
    """A subscribed queue's URL and policy statements; None when the queue no longer exists."""
    sqs = aws.sqs()
    try:
        url = sqs.get_queue_url(QueueName=arn.rsplit(":", 1)[-1])["QueueUrl"]
    except ClientError as exc:
        if "NonExistentQueue" in error_code(exc) or "QueueDoesNotExist" in error_code(exc):
            return None
        raise
    policy = sqs.get_queue_attributes(QueueUrl=url, AttributeNames=["Policy"])
    return url, _statements(policy.get("Attributes", {}).get("Policy", ""))


def check(aws: Aws, ctx: ScenarioContext) -> CheckResult:
    topic = _topic_arn(aws, ctx)
    if topic is None:
        return gone(f"Topic {ctx.prefix}-orders")
    subscriptions = aws.sns().list_subscriptions_by_topic(TopicArn=topic).get("Subscriptions", [])
    queue_arns = sorted({s["Endpoint"] for s in subscriptions if s.get("Protocol") == "sqs"})
    queues: dict[str, tuple[str, list[dict[str, object]]]] = {}
    missing: list[str] = []
    for arn in queue_arns:
        name = arn.rsplit(":", 1)[-1]
        found = _queue(aws, arn)
        if found is None:
            missing.append(name)
        else:
            queues[name] = found
    sending = {n for n, (_, st) in queues.items() if any(_lets_sns_send(s) for s in st)}
    scoped = {
        n
        for n, (_, st) in queues.items()
        if any(_lets_sns_send(s) and _scoped_to(s, topic) for s in st)
    }
    token = f"istari-{secrets.token_hex(4)}"
    aws.sns().publish(TopicArn=topic, Message=json.dumps({"order": token}))
    reached = _delivered(aws, {n: url for n, (url, _) in queues.items()}, token)
    names = sorted(queues)
    clauses = [
        Clause(
            len(queues) >= 2,
            f"{len(queues)} queues subscribed: {', '.join(names)}",
            f"subscribe two queues to the topic ({len(queues)} so far)",
        ),
        Clause(
            bool(queues) and sending == set(queues),
            "every queue's policy lets SNS send",
            "queue policy must allow sns.amazonaws.com to sqs:SendMessage: "
            + (", ".join(sorted(set(queues) - sending)) or "no queue yet"),
        ),
        Clause(
            bool(queues) and scoped == set(queues),
            "every queue policy is scoped to this topic with aws:SourceArn",
            "scope each queue policy to the topic with an aws:SourceArn condition: "
            + (", ".join(sorted(set(queues) - scoped)) or "no queue yet"),
        ),
        Clause(
            bool(queues) and reached == set(queues),
            "one published message reached every subscribed queue",
            "the published message did not reach: "
            + (", ".join(sorted(set(queues) - reached)) or "no queue yet"),
        ),
    ]
    header = f"Topic {topic}: {len(subscriptions)} subscription(s), {len(queues)} SQS queue(s)"
    if missing:
        header += f"; subscribed but deleted: {', '.join(missing)}"
    return verdict(header, clauses, "one order event fans out to every queue")


def solve(aws: Aws, ctx: ScenarioContext) -> None:
    topic = _topic_arn(aws, ctx)
    if topic is None:
        raise RuntimeError(f"no topic {ctx.prefix}-orders: run the setup first")
    sqs, sns = aws.sqs(), aws.sns()
    for role in ("billing", "shipping"):
        url = sqs.create_queue(QueueName=f"{ctx.prefix}-{role}")["QueueUrl"]
        arn = sqs.get_queue_attributes(QueueUrl=url, AttributeNames=["QueueArn"])["Attributes"][
            "QueueArn"
        ]
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": SNS_SERVICE},
                    "Action": "sqs:SendMessage",
                    "Resource": arn,
                    "Condition": {"ArnEquals": {"aws:SourceArn": topic}},
                }
            ],
        }
        sqs.set_queue_attributes(QueueUrl=url, Attributes={"Policy": json.dumps(policy)})
        sns.subscribe(TopicArn=topic, Protocol="sqs", Endpoint=arn)


def teardown(aws: Aws, ctx: ScenarioContext) -> None:
    sns, sqs = aws.sns(), aws.sqs()
    for topic in sns.list_topics().get("Topics", []):
        arn = topic.get("TopicArn", "")
        if arn.rsplit(":", 1)[-1].startswith(ctx.scenario_prefix):
            for sub in sns.list_subscriptions_by_topic(TopicArn=arn).get("Subscriptions", []):
                if sub.get("SubscriptionArn", "").startswith("arn:"):
                    sns.unsubscribe(SubscriptionArn=sub["SubscriptionArn"])
            sns.delete_topic(TopicArn=arn)
    for url in sqs.list_queues(QueueNamePrefix=ctx.scenario_prefix).get("QueueUrls", []):
        sqs.delete_queue(QueueUrl=url)


SCENARIO = Scenario(
    id="sns-sqs-fanout",
    profile="saa",
    title="Fan out with SNS and SQS: one order event, two queues",
    context=(
        "Setup creates an SNS topic in the emulator whose name starts with istari-sns-sqs-"
        "fanout- and ends in -orders; the setup output gives its ARN and the prefix to name "
        "your queues with. Nothing is subscribed yet."
    ),
    task=(
        "Billing and shipping each need every order event, and neither may slow the other "
        "down. Create two SQS queues named with the run's prefix, subscribe both to the topic, "
        "and give each a queue policy that lets the SNS service send to it, scoped to this "
        "topic with an aws:SourceArn condition. Use the AWS CLI pointed at the emulator, then "
        "run the check: it publishes one message and looks for it in every subscribed queue."
    ),
    hint=(
        "sqs create-queue, then sqs set-queue-attributes with a Policy allowing Principal "
        '{"Service": "sns.amazonaws.com"} the action sqs:SendMessage on the queue ARN with '
        '{"ArnEquals": {"aws:SourceArn": "<the topic ARN>"}}, then sns subscribe '
        "--protocol sqs --notification-endpoint <the queue ARN>. Twice."
    ),
    setup=setup,
    check=check,
    teardown=teardown,
    solve=solve,
)
