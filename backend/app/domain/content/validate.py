"""Cross-reference validation for a pack, beyond what the schema can express."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field

from pydantic import ValidationError as PydanticValidationError

from app.domain.content.schemas.common import ItemBase
from app.domain.content.schemas.pack import ContentPackSpec
from app.domain.exceptions import ValidationError


@dataclass(frozen=True, slots=True)
class Issue:
    code: str
    message: str
    item_key: str | None = None


@dataclass(slots=True)
class ValidationReport:
    errors: list[Issue] = field(default_factory=list)
    warnings: list[Issue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "errors": [asdict(issue) for issue in self.errors],
            "warnings": [asdict(issue) for issue in self.warnings],
        }


def parse_pack(data: object) -> ContentPackSpec:
    """Schema-validate raw JSON. Raises ValidationError with the pydantic details."""
    try:
        return ContentPackSpec.model_validate(data)
    except PydanticValidationError as exc:
        issues = [
            {"loc": ".".join(str(p) for p in e["loc"]), "msg": e["msg"]} for e in exc.errors()
        ]
        raise ValidationError(
            "content pack failed schema validation", details={"issues": issues}
        ) from exc


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def validate_pack(pack: ContentPackSpec) -> ValidationReport:
    report = ValidationReport()
    objective_codes = {o.code for d in pack.domains for o in d.objectives}

    weight_total = sum(d.weight_percent for d in pack.domains)
    if weight_total != 100:
        report.errors.append(Issue("weights", f"domain weights sum to {weight_total}, not 100"))
    domain_codes = [d.code for d in pack.domains]
    if len(set(domain_codes)) != len(domain_codes):
        report.errors.append(Issue("domains", "duplicate domain codes"))

    all_items: list[ItemBase] = [*pack.lessons, *pack.questions, *pack.flashcards, *pack.labs]
    seen_keys: set[str] = set()
    for item in all_items:
        if item.key in seen_keys:
            report.errors.append(Issue("duplicate_key", "item key used twice", item.key))
        seen_keys.add(item.key)
        for code in item.objectives:
            if code not in objective_codes:
                report.errors.append(
                    Issue("unknown_objective", f"objective {code} is not in this pack", item.key)
                )
        if item.provenance.authored_by == "ai" and item.review_status == "human_reviewed":
            report.warnings.append(
                Issue(
                    "provenance",
                    "AI-authored item marked human_reviewed — confirm a human actually reviewed it",
                    item.key,
                )
            )

    stems: dict[str, str] = {}
    for question in pack.questions:
        key = _normalise(question.stem_md)
        if key in stems:
            report.warnings.append(
                Issue("duplicate_stem", f"stem duplicates {stems[key]}", question.key)
            )
        stems[key] = question.key

    return report


def content_hash(item: ItemBase) -> str:
    """Stable hash of an item's content so re-imports can detect 'unchanged'."""
    payload = json.dumps(item.model_dump(mode="json"), sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
