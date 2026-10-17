"""Enough IAM policy evaluation to grade a least-privilege lab by reading the policies back.

The emulator enforces IAM, but moto, which the tests use, does not, so the grade comes from
the policies themselves, read the same way from either. Every policy that reaches a user
counts: its inline and attached policies, and its groups'. An explicit Deny wins; otherwise
an Allow is needed. `Action`/`NotAction` match case-insensitively and `Resource`/`NotResource`
case-sensitively, both with IAM's `*` and `?` wildcards. A statement with a `Condition` is
left out and named, since this lab needs none.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from fnmatch import fnmatchcase
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types_boto3_iam.client import IAMClient


@dataclass(frozen=True, slots=True)
class Statement:
    effect: str
    actions: tuple[str, ...]
    resources: tuple[str, ...]
    # True when the list came from NotAction / NotResource.
    not_actions: bool = False
    not_resources: bool = False
    sid: str = ""


def _strings(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, list):
        return tuple(str(v) for v in value)
    return ()


def statements(document: object) -> tuple[list[Statement], list[str]]:
    """A policy document (a dict, or its JSON) as statements, and the Sids left out because
    they carry a Condition."""
    doc = json.loads(document) if isinstance(document, str) else document
    raw = doc.get("Statement", []) if isinstance(doc, dict) else []
    found: list[Statement] = []
    skipped: list[str] = []
    for item in raw if isinstance(raw, list) else [raw]:
        if not isinstance(item, dict):
            continue
        sid = str(item.get("Sid", ""))
        if item.get("Condition"):
            skipped.append(sid or "(no Sid)")
            continue
        found.append(
            Statement(
                effect=str(item.get("Effect", "")),
                actions=_strings(item.get("Action", item.get("NotAction"))),
                resources=_strings(item.get("Resource", item.get("NotResource"))),
                not_actions="NotAction" in item,
                not_resources="NotResource" in item,
                sid=sid,
            )
        )
    return found, skipped


def _matches(statement: Statement, action: str, resource: str) -> bool:
    action_hit = any(fnmatchcase(action.lower(), a.lower()) for a in statement.actions)
    resource_hit = any(fnmatchcase(resource, r) for r in statement.resources)
    return (action_hit != statement.not_actions) and (resource_hit != statement.not_resources)


def allowed(granted: Iterable[Statement], action: str, resource: str) -> bool:
    hits = [s for s in granted if _matches(s, action, resource)]
    if any(s.effect == "Deny" for s in hits):
        return False
    return any(s.effect == "Allow" for s in hits)


def _managed(iam: IAMClient, arn: str) -> object:
    version = iam.get_policy(PolicyArn=arn)["Policy"].get("DefaultVersionId", "v1")
    return iam.get_policy_version(PolicyArn=arn, VersionId=version)["PolicyVersion"].get("Document")


def user_documents(iam: IAMClient, user: str) -> list[object]:
    """Every policy document that reaches the user: inline, attached, and its groups' too."""
    docs: list[object] = [
        iam.get_user_policy(UserName=user, PolicyName=name)["PolicyDocument"]
        for name in iam.list_user_policies(UserName=user)["PolicyNames"]
    ]
    docs += [
        _managed(iam, p["PolicyArn"])
        for p in iam.list_attached_user_policies(UserName=user)["AttachedPolicies"]
        if "PolicyArn" in p
    ]
    for group in iam.list_groups_for_user(UserName=user)["Groups"]:
        name = group["GroupName"]
        docs += [
            iam.get_group_policy(GroupName=name, PolicyName=policy)["PolicyDocument"]
            for policy in iam.list_group_policies(GroupName=name)["PolicyNames"]
        ]
        docs += [
            _managed(iam, p["PolicyArn"])
            for p in iam.list_attached_group_policies(GroupName=name)["AttachedPolicies"]
            if "PolicyArn" in p
        ]
    return docs
