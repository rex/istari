"""S3 versioning: the smallest real AWS lab, and the adapter's own end-to-end scenario.

Setup makes an empty bucket with versioning off; the learner turns versioning on; the check
reads the bucket's versioning status back.
"""

from __future__ import annotations

from botocore.exceptions import ClientError

from app.adapters.localemu.aws import Aws
from app.adapters.localemu.scenario import Scenario, ScenarioContext
from app.adapters.localemu.scenarios.s3_util import delete_buckets, error_code
from app.domain.verifier import CheckResult


def setup(aws: Aws, ctx: ScenarioContext) -> str:
    aws.s3().create_bucket(Bucket=ctx.prefix)
    return f"Bucket {ctx.prefix} is ready, with versioning off."


def check(aws: Aws, ctx: ScenarioContext) -> CheckResult:
    try:
        status = aws.s3().get_bucket_versioning(Bucket=ctx.prefix).get("Status", "")
    except ClientError as exc:
        if error_code(exc) == "NoSuchBucket":
            # Deleted, or the emulator restarted (its state is ephemeral): ungradable, not a fail.
            return CheckResult(
                passed=False,
                unavailable_reason=f"Bucket {ctx.prefix} is gone; set the lab up again.",
            )
        raise
    if status == "Enabled":
        return CheckResult(
            passed=True, output=f"Bucket {ctx.prefix}: versioning Enabled\nPASS: versioning is on"
        )
    shown = status or "never enabled"
    return CheckResult(
        passed=False, output=f"Bucket {ctx.prefix}: versioning {shown}\nFAIL: versioning is off"
    )


def teardown(aws: Aws, ctx: ScenarioContext) -> None:
    delete_buckets(aws.s3(), ctx.scenario_prefix)


SCENARIO = Scenario(
    id="s3-versioning",
    profile="saa",
    title="Turn on versioning for an S3 bucket",
    context=(
        "Setup creates an empty bucket in the emulator with versioning off; "
        "the setup output names it (it starts with istari-s3-versioning-)."
    ),
    task=(
        "Turn on versioning for that bucket, so an overwritten or deleted object can be "
        "recovered from an earlier version. Use the AWS CLI pointed at the emulator, "
        "then run the check."
    ),
    hint=(
        "aws s3api put-bucket-versioning --bucket <the bucket> "
        "--versioning-configuration Status=Enabled"
    ),
    setup=setup,
    check=check,
    teardown=teardown,
)
