"""Every LocalEmu scenario Istari can set up and grade, by id."""

from __future__ import annotations

from app.adapters.localemu.scenario import ScenarioRegistry
from app.adapters.localemu.scenarios import s3_lifecycle, s3_versioning

REGISTRY = ScenarioRegistry([s3_lifecycle.SCENARIO, s3_versioning.SCENARIO])

__all__ = ["REGISTRY"]
