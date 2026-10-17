"""Every LocalEmu scenario Istari can set up and grade, by id."""

from __future__ import annotations

from app.adapters.localemu.scenario import ScenarioRegistry
from app.adapters.localemu.scenarios import (
    iam_least_privilege,
    s3_lifecycle,
    s3_versioning,
    sns_sqs_fanout,
    vpc_public_private,
)

REGISTRY = ScenarioRegistry(
    [
        iam_least_privilege.SCENARIO,
        s3_lifecycle.SCENARIO,
        s3_versioning.SCENARIO,
        sns_sqs_fanout.SCENARIO,
        vpc_public_private.SCENARIO,
    ]
)

__all__ = ["REGISTRY"]
