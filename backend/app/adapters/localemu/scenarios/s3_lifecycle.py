"""S3 lifecycle: archive the logs at 30 days, delete them at a year, leave the reports alone.

Setup makes a bucket holding one object under `logs/` and one under `reports/`, with no
lifecycle rules. The learner adds a rule for `logs/` only: transition to S3 Glacier Flexible
Retrieval (`GLACIER`) 30 days after creation and expire 365 days after creation, the S3 FAQ's
own example. Flexible Retrieval's minimum storage duration is 90 days, so expiring at 365
carries no early-deletion charge. The check reads the configuration back and grades each
clause on its own line.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from botocore.exceptions import ClientError

from app.adapters.localemu.aws import Aws
from app.adapters.localemu.scenario import Scenario, ScenarioContext
from app.adapters.localemu.scenarios.s3_util import delete_buckets, error_code
from app.domain.verifier import CheckResult

if TYPE_CHECKING:
    from types_boto3_s3.type_defs import LifecycleRuleOutputTypeDef, LifecycleRuleTypeDef

LOGS = "logs/"
LOG_KEY = "logs/app-2026-10-01.log"
REPORT_KEY = "reports/q3-costs.csv"
ARCHIVE_CLASS = "GLACIER"
ARCHIVE_DAYS = 30
EXPIRE_DAYS = 365


def setup(aws: Aws, ctx: ScenarioContext) -> str:
    s3 = aws.s3()
    s3.create_bucket(Bucket=ctx.prefix)
    s3.put_object(Bucket=ctx.prefix, Key=LOG_KEY, Body=b"2026-10-01T00:00:00Z app started\n")
    s3.put_object(Bucket=ctx.prefix, Key=REPORT_KEY, Body=b"service,cost\ns3,1.00\n")
    return (
        f"Bucket {ctx.prefix} is ready, holding {LOG_KEY} and {REPORT_KEY}, "
        "with no lifecycle rules."
    )


def _scope(rule: LifecycleRuleOutputTypeDef) -> tuple[str, bool]:
    """The key prefix a rule acts on ('' is the whole bucket), and whether tags or object
    sizes narrow it further. A rule may carry its prefix the old way, outside `Filter`."""
    if "Filter" not in rule:
        return rule.get("Prefix", ""), False
    narrowing = rule["Filter"]
    if "And" in narrowing:
        both = narrowing["And"]
        sized = "ObjectSizeGreaterThan" in both or "ObjectSizeLessThan" in both
        return both.get("Prefix", ""), bool(both.get("Tags")) or sized
    sized = "ObjectSizeGreaterThan" in narrowing or "ObjectSizeLessThan" in narrowing
    return narrowing.get("Prefix", ""), "Tag" in narrowing or sized


def _rules(aws: Aws, bucket: str) -> list[LifecycleRuleOutputTypeDef] | None:
    """The bucket's rules ([] with no configuration); None when the bucket is gone."""
    try:
        return aws.s3().get_bucket_lifecycle_configuration(Bucket=bucket).get("Rules", [])
    except ClientError as exc:
        if error_code(exc) == "NoSuchBucket":
            return None
        if error_code(exc) == "NoSuchLifecycleConfiguration":
            return []
        raise


def check(aws: Aws, ctx: ScenarioContext) -> CheckResult:
    rules = _rules(aws, ctx.prefix)
    if rules is None:
        return CheckResult(
            passed=False, unavailable_reason=f"Bucket {ctx.prefix} is gone; set the lab up again."
        )
    enabled = [r for r in rules if r.get("Status") == "Enabled"]
    logs_rules = [r for r in enabled if _scope(r) == (LOGS, False)]
    transitions = [t for r in logs_rules for t in r.get("Transitions", [])]
    archived = any(
        t.get("Days") == ARCHIVE_DAYS and t.get("StorageClass") == ARCHIVE_CLASS
        for t in transitions
    )
    expired = any(r.get("Expiration", {}).get("Days") == EXPIRE_DAYS for r in logs_rules)
    touching = [
        r.get("ID") or "(no id)"
        for r in enabled
        if not _scope(r)[1] and REPORT_KEY.startswith(_scope(r)[0])
    ]
    found = ", ".join(
        f"{t.get('StorageClass', '?')} at {t.get('Days', '?')} days" for t in transitions
    )
    clauses = [
        (
            bool(logs_rules),
            f"an enabled rule scoped to {LOGS}",
            f"no enabled rule is scoped to exactly {LOGS} (no tag or size filter)",
        ),
        (
            archived,
            f"{LOGS} moves to {ARCHIVE_CLASS} {ARCHIVE_DAYS} days after creation",
            f"{LOGS} must move to {ARCHIVE_CLASS} {ARCHIVE_DAYS} days after creation"
            + (f" (found: {found})" if found else ""),
        ),
        (
            expired,
            f"{LOGS} expires {EXPIRE_DAYS} days after creation",
            f"{LOGS} must expire {EXPIRE_DAYS} days after creation",
        ),
        (
            not touching,
            "reports/ is left alone",
            f"rule {', '.join(touching)} also acts on {REPORT_KEY}",
        ),
    ]
    lines = [f"Bucket {ctx.prefix}: {len(rules)} lifecycle rule(s), {len(enabled)} enabled"]
    lines += [f"[{'ok' if ok else '--'}] {good if ok else bad}" for ok, good, bad in clauses]
    failed = next((bad for ok, _good, bad in clauses if not ok), None)
    if failed is None:
        lines.append(f"PASS: {LOGS} archives at {ARCHIVE_DAYS} days and expires at {EXPIRE_DAYS}")
        return CheckResult(passed=True, output="\n".join(lines))
    lines.append(f"FAIL: {failed}")
    return CheckResult(passed=False, output="\n".join(lines))


def solve(aws: Aws, ctx: ScenarioContext) -> None:
    rule: LifecycleRuleTypeDef = {
        "ID": "archive-then-expire-logs",
        "Filter": {"Prefix": LOGS},
        "Status": "Enabled",
        "Transitions": [{"Days": ARCHIVE_DAYS, "StorageClass": "GLACIER"}],
        "Expiration": {"Days": EXPIRE_DAYS},
    }
    aws.s3().put_bucket_lifecycle_configuration(
        Bucket=ctx.prefix, LifecycleConfiguration={"Rules": [rule]}
    )


def teardown(aws: Aws, ctx: ScenarioContext) -> None:
    delete_buckets(aws.s3(), ctx.scenario_prefix)


SCENARIO = Scenario(
    id="s3-lifecycle",
    profile="saa",
    title="Archive the logs, keep the reports: an S3 lifecycle rule",
    context=(
        "Setup creates a bucket in the emulator (its name starts with istari-s3-lifecycle-; "
        f"the setup output names it) holding one application log under {LOGS} and one cost "
        "report under reports/. It has no lifecycle rules."
    ),
    task=(
        "The logs are read for a month, kept for a year for audits, then never needed. Add a "
        f"lifecycle rule that moves objects under {LOGS} to S3 Glacier Flexible Retrieval "
        f"{ARCHIVE_DAYS} days after creation and deletes them {EXPIRE_DAYS} days after "
        "creation. The reports are read all the time, so the rule must not touch reports/. "
        "Use the AWS CLI pointed at the emulator, then run the check."
    ),
    hint=(
        "aws s3api put-bucket-lifecycle-configuration --bucket <the bucket> "
        "--lifecycle-configuration file://lifecycle.json, where lifecycle.json holds one rule: "
        f'Filter {{"Prefix": "{LOGS}"}}, Status Enabled, Transitions '
        f'[{{"Days": {ARCHIVE_DAYS}, "StorageClass": "{ARCHIVE_CLASS}"}}] and Expiration '
        f'{{"Days": {EXPIRE_DAYS}}}.'
    ),
    setup=setup,
    check=check,
    teardown=teardown,
    solve=solve,
)
