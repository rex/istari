"""IAM least privilege: let an analyst read the reports and nothing else.

Setup makes a bucket holding `reports/q3-summary.csv` and `payroll/2026-10.csv`, and a user,
`<prefix>-analyst`, with an access key and no permissions. The learner writes the policy that
lets the analyst `s3:GetObject` under `reports/` only. The check reads every policy that
reaches the user (inline, attached, groups') and asks four questions of it: can it read a
report, can it read payroll, can it write a report, can it read another bucket. Only the first
may be yes. In the emulator, identity is the access key id, so the learner can also try the
analyst's calls for real with the key id setup prints; the emulator enforces IAM.
"""

from __future__ import annotations

import json

from botocore.exceptions import ClientError

from app.adapters.localemu.aws import Aws
from app.adapters.localemu.scenario import Scenario, ScenarioContext
from app.adapters.localemu.scenarios.grading import Clause, gone, verdict
from app.adapters.localemu.scenarios.iam_eval import allowed, statements, user_documents
from app.adapters.localemu.scenarios.s3_util import delete_buckets, error_code
from app.domain.verifier import CheckResult

REPORT_KEY = "reports/q3-summary.csv"
PAYROLL_KEY = "payroll/2026-10.csv"


def _user(ctx: ScenarioContext) -> str:
    return f"{ctx.prefix}-analyst"


def setup(aws: Aws, ctx: ScenarioContext) -> str:
    s3, iam = aws.s3(), aws.iam()
    s3.create_bucket(Bucket=ctx.prefix)
    s3.put_object(Bucket=ctx.prefix, Key=REPORT_KEY, Body=b"region,revenue\nus-east-1,100\n")
    s3.put_object(Bucket=ctx.prefix, Key=PAYROLL_KEY, Body=b"employee,salary\nredacted,0\n")
    iam.create_user(UserName=_user(ctx))
    key = iam.create_access_key(UserName=_user(ctx))["AccessKey"]["AccessKeyId"]
    return (
        f"Bucket {ctx.prefix} holds {REPORT_KEY} and {PAYROLL_KEY}. "
        f"User {_user(ctx)} has no permissions yet; its access key id is {key} "
        "(in the emulator the key id is the identity, so any secret works)."
    )


def check(aws: Aws, ctx: ScenarioContext) -> CheckResult:
    iam = aws.iam()
    try:
        documents = user_documents(iam, _user(ctx))
    except ClientError as exc:
        if error_code(exc) == "NoSuchEntity":
            return gone(f"User {_user(ctx)}")
        raise
    granted, skipped = [], []
    for document in documents:
        found, conditional = statements(document)
        granted += found
        skipped += conditional
    bucket = f"arn:aws:s3:::{ctx.prefix}"
    clauses = [
        Clause(
            allowed(granted, "s3:GetObject", f"{bucket}/{REPORT_KEY}"),
            f"the analyst can read {REPORT_KEY}",
            f"the analyst must be able to s3:GetObject on {ctx.prefix}/reports/*",
        ),
        Clause(
            not allowed(granted, "s3:GetObject", f"{bucket}/{PAYROLL_KEY}"),
            f"the analyst cannot read {PAYROLL_KEY}",
            "the analyst can read payroll/: narrow the Resource to the reports/ prefix",
        ),
        Clause(
            not allowed(granted, "s3:PutObject", f"{bucket}/{REPORT_KEY}"),
            "the analyst cannot write to reports/",
            "the analyst can write to reports/: allow s3:GetObject and nothing more",
        ),
        Clause(
            not allowed(granted, "s3:GetObject", f"arn:aws:s3:::istari-elsewhere/{REPORT_KEY}"),
            "the analyst cannot read any other bucket",
            "the analyst can read other buckets: name this bucket in the Resource",
        ),
    ]
    header = f"User {_user(ctx)}: {len(documents)} policy document(s), {len(granted)} statement(s)"
    if skipped:
        header += f"; not evaluated (they carry a Condition): {', '.join(skipped)}"
    return verdict(header, clauses, "the analyst reads reports/ and nothing else")


def solve(aws: Aws, ctx: ScenarioContext) -> None:
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "ReadReportsOnly",
                "Effect": "Allow",
                "Action": "s3:GetObject",
                "Resource": f"arn:aws:s3:::{ctx.prefix}/reports/*",
            }
        ],
    }
    aws.iam().put_user_policy(
        UserName=_user(ctx), PolicyName="read-reports", PolicyDocument=json.dumps(policy)
    )


def _delete_user(aws: Aws, user: str) -> None:
    iam = aws.iam()
    for name in iam.list_user_policies(UserName=user)["PolicyNames"]:
        iam.delete_user_policy(UserName=user, PolicyName=name)
    for attached in iam.list_attached_user_policies(UserName=user)["AttachedPolicies"]:
        iam.detach_user_policy(UserName=user, PolicyArn=attached.get("PolicyArn", ""))
    for group in iam.list_groups_for_user(UserName=user)["Groups"]:
        iam.remove_user_from_group(UserName=user, GroupName=group["GroupName"])
    for key in iam.list_access_keys(UserName=user)["AccessKeyMetadata"]:
        iam.delete_access_key(UserName=user, AccessKeyId=key.get("AccessKeyId", ""))
    iam.delete_user(UserName=user)


def _delete_group(aws: Aws, group: str) -> None:
    iam = aws.iam()
    for name in iam.list_group_policies(GroupName=group)["PolicyNames"]:
        iam.delete_group_policy(GroupName=group, PolicyName=name)
    for attached in iam.list_attached_group_policies(GroupName=group)["AttachedPolicies"]:
        iam.detach_group_policy(GroupName=group, PolicyArn=attached.get("PolicyArn", ""))
    for user in iam.get_group(GroupName=group)["Users"]:
        iam.remove_user_from_group(GroupName=group, UserName=user["UserName"])
    iam.delete_group(GroupName=group)


def _delete_policy(aws: Aws, arn: str) -> None:
    iam = aws.iam()
    for version in iam.list_policy_versions(PolicyArn=arn)["Versions"]:
        if not version.get("IsDefaultVersion"):
            iam.delete_policy_version(PolicyArn=arn, VersionId=version.get("VersionId", ""))
    iam.delete_policy(PolicyArn=arn)


def teardown(aws: Aws, ctx: ScenarioContext) -> None:
    """Every user, group and customer-managed policy named with the scenario's prefix, and its
    buckets. A learner's own extras go too when they carry the prefix."""
    iam = aws.iam()
    for user in iam.list_users()["Users"]:
        if user["UserName"].startswith(ctx.scenario_prefix):
            _delete_user(aws, user["UserName"])
    for group in iam.list_groups()["Groups"]:
        if group["GroupName"].startswith(ctx.scenario_prefix):
            _delete_group(aws, group["GroupName"])
    for policy in iam.list_policies(Scope="Local")["Policies"]:
        if policy.get("PolicyName", "").startswith(ctx.scenario_prefix):
            _delete_policy(aws, policy.get("Arn", ""))
    delete_buckets(aws.s3(), ctx.scenario_prefix)


SCENARIO = Scenario(
    id="iam-least-privilege",
    profile="saa",
    title="Least privilege: an analyst who reads the reports and nothing else",
    context=(
        "Setup creates a bucket in the emulator (its name starts with istari-iam-least-"
        f"privilege-) holding {REPORT_KEY} and {PAYROLL_KEY}, and a user named after the "
        "bucket with -analyst on the end, which has an access key and no permissions. The "
        "setup output names both and prints the analyst's key id."
    ),
    task=(
        "Give the analyst exactly what the job needs: read the objects under reports/ in that "
        "bucket. It must not read payroll/, write anything, or read any other bucket. Attach "
        "the policy to the user (inline or managed) with the AWS CLI pointed at the emulator, "
        "then run the check. To see it bite, repeat a read as the analyst by setting "
        "AWS_ACCESS_KEY_ID to its key id: reports/ answers, payroll/ is denied."
    ),
    hint=(
        "aws iam put-user-policy --user-name <the analyst> --policy-name read-reports "
        "--policy-document file://policy.json, where policy.json allows Action s3:GetObject "
        "on Resource arn:aws:s3:::<the bucket>/reports/* and nothing else."
    ),
    setup=setup,
    check=check,
    teardown=teardown,
    solve=solve,
)
