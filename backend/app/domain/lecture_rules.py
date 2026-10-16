"""Title rules that outrank or steer the ranking: objective codes named in a lecture's or
section's title or file name, and a domain's distinctive word in a title. Pure."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping

from app.domain.lecture_text import tokenize

_OBJECTIVE_CODE = re.compile(r"\bobj(?:ective)?[-_ ]?(\d{1,2})[-_.](\d{1,2})\b", re.IGNORECASE)
# "obj-1-1-and-1-2": further codes chained onto an explicit one.
_CHAINED_CODE = re.compile(r"[-_ ]*(?:and|&|,)[-_ ]*(\d{1,2})[-_.](\d{1,2})\b", re.IGNORECASE)
_LEADING_CODE = re.compile(r"^\s*(\d{1,2})\.(\d{1,2})(?![\d.])")


def rule_codes(titles: Iterable[str], codes: Iterable[str]) -> list[str]:
    """Objective codes named outright in a lecture's or section's title or file name:
    "obj-1-1", "Objective 2.3", or a title that starts with "1.3". Only codes the track
    has count; order follows the titles."""
    known = set(codes)
    found: list[str] = []
    for title in titles:
        candidates: list[str] = []
        for match in _OBJECTIVE_CODE.finditer(title):
            candidates.append(f"{match.group(1)}.{match.group(2)}")
            position = match.end()
            while chained := _CHAINED_CODE.match(title, position):
                candidates.append(f"{chained.group(1)}.{chained.group(2)}")
                position = chained.end()
        leading = _LEADING_CODE.match(title)
        if leading:
            candidates.append(f"{leading.group(1)}.{leading.group(2)}")
        for code in candidates:
            if code in known and code not in found:
                found.append(code)
    return found


def distinctive_domain_terms(domains: Mapping[str, str]) -> dict[str, set[str]]:
    """Per domain, the words of its name no other domain's name uses: "secure" for
    "Design Secure Architectures" next to "Design Resilient Architectures"."""
    tokens = {code: set(tokenize(name)) for code, name in domains.items()}
    return {
        code: {
            term
            for term in terms
            if not any(term in other for other_code, other in tokens.items() if other_code != code)
        }
        for code, terms in tokens.items()
    }


def domain_hints(titles: Iterable[str], distinctive: Mapping[str, set[str]]) -> set[str]:
    """Domains whose distinctive words appear in the lecture's or section's title."""
    words: set[str] = set()
    for title in titles:
        words.update(tokenize(title))
    return {code for code, terms in distinctive.items() if terms & words}
