"""Names to slugs, exam hints and sort keys: shared by the corpus tooling and the catalog."""

from __future__ import annotations

import re
from dataclasses import dataclass

_EXAM_CODE = re.compile(r"\b(SAA|SOA|DOP|DVA|SCS|CLF|ANS|SAP|MLS|DAS|DBS|PAS)-C0\d\b", re.I)
_K8S_CODE = re.compile(r"\b(CKA|CKAD|CKS|KCNA|KCSA)\b")
_YEAR = re.compile(r"\b(20[12]\d)\b")
_NON_SLUG = re.compile(r"[^a-z0-9]+")
_NUMBER = re.compile(r"(\d+)")
_JUNK = re.compile(
    r"(FreeCourse|FTUForum|Bookflare|Visit For More|Downloaded From|How you can help|\.DS_Store)",
    re.I,
)


@dataclass(frozen=True, slots=True)
class ExamHint:
    code: str | None
    year: int | None


def infer_exam(name: str) -> ExamHint:
    """Best-effort exam code and year from a course name, e.g. "... 2021 [SOA-C02]"."""
    code_match = _EXAM_CODE.search(name) or _K8S_CODE.search(name)
    year_match = _YEAR.search(name)
    return ExamHint(
        code=code_match.group(0).upper() if code_match else None,
        year=int(year_match.group(1)) if year_match else None,
    )


def slugify(text: str, max_length: int = 80) -> str:
    slug = _NON_SLUG.sub("-", text.lower()).strip("-")
    return slug[:max_length].strip("-") or "untitled"


def natural_key(text: str) -> tuple[object, ...]:
    """Sort "2 - IAM" before "10 - VPC": digit runs compare as numbers."""
    return tuple(int(part) if part.isdigit() else part.casefold() for part in _NUMBER.split(text))


def is_junk_name(name: str) -> bool:
    """Tracker advertising, link files and OS droppings that ship inside downloaded courses."""
    return bool(_JUNK.search(name))
