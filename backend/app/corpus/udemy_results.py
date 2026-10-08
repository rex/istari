"""Parse the text of a Udemy practice-test results PDF (pdftotext output) into questions.

The results page prints, per question: `Question N: Correct|Incorrect|Skipped`, the
stem, the options as blank-line-separated paragraphs with `(Correct)` on its own line
after each right one (and `(Incorrect)` after a wrong pick), then `Explanation` with
`Correct option(s):`, `Incorrect options:` (each "<option> - <why>") and
`References:` (documentation URLs, sometimes wrapped across lines).

The stem and the first option share a paragraph. The explanation restates every option
verbatim, so the split is chosen where the remainder of that paragraph reappears in the
explanation; a trailing question mark is only the first guess. Tested against a
synthetic copy of the shape.
"""

from __future__ import annotations

import re

from app.corpus.private_pack import ParsedQuestion

_HEADER = re.compile(r"^Question (?P<n>\d+): (?P<status>\w+)\s*$")
_MARK = re.compile(r"^\((?P<kind>Correct|Incorrect)\)\s*$")
_INLINE_MARK = re.compile(r"\s*\((?P<kind>Correct|Incorrect)\)\s*$")
_SELECT_HINT = re.compile(r"\b(select|choose)\b.*\b(two|three|2|3)\b", re.I)
_SPACE = re.compile(r"\s+")
# Udemy's results PDFs bullet options with an en dash (U+2013) as often as a hyphen; the
# character is spelled out so the source holds no look-alike dash.
_LEADING_DASH = re.compile("^[\\s\\-" + chr(0x2013) + ":]+")
RATIONALE_KEY_LENGTH = 60
OPTION_KEY_LENGTH = 50


def _norm(lines: list[str]) -> str:
    return _SPACE.sub(" ", " ".join(line.strip() for line in lines)).strip()


def _paragraphs(lines: list[str]) -> list[list[str]]:
    paragraphs: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if line.strip():
            current.append(line.strip())
        elif current:
            paragraphs.append(current)
            current = []
    if current:
        paragraphs.append(current)
    return paragraphs


def _looks_like_option(lines: list[str], explanation: str) -> bool:
    text = _norm(lines).casefold()
    return len(text) >= 6 and text[:OPTION_KEY_LENGTH] in explanation


def _split_stem(paragraph: list[str], explanation: str) -> tuple[list[str], list[str]]:
    """Where the stem ends and the first option begins, inside their shared paragraph."""
    if len(paragraph) < 2:
        return paragraph, []
    asked = [
        i + 1
        for i, line in enumerate(paragraph[:-1])
        if line.rstrip().endswith("?") or _SELECT_HINT.search(line)
    ]
    if asked and _looks_like_option(paragraph[asked[-1] :], explanation):
        return paragraph[: asked[-1]], paragraph[asked[-1] :]
    for k in range(1, len(paragraph)):
        if _looks_like_option(paragraph[k:], explanation):
            return paragraph[:k], paragraph[k:]
    if asked:
        return paragraph[: asked[-1]], paragraph[asked[-1] :]
    return paragraph, []


def _options(paragraphs: list[list[str]]) -> tuple[list[str], list[int]]:
    options: list[str] = []
    correct: list[int] = []
    for paragraph in paragraphs:
        if len(paragraph) == 1 and (mark := _MARK.match(paragraph[0])):
            if options and mark.group("kind") == "Correct" and (len(options) - 1) not in correct:
                correct.append(len(options) - 1)
            continue
        text = _norm(paragraph)
        inline = _INLINE_MARK.search(text)
        if inline:
            text = _INLINE_MARK.sub("", text)
            if inline.group("kind") == "Correct":
                correct.append(len(options))
        if text:
            options.append(text)
    return options, correct


def _rationales(options: list[str], correct: list[int], text: str) -> dict[int, str]:
    """Match each "<option> - <why>" entry back to its option by the option's text."""
    folded = text.casefold()
    found: list[tuple[int, int, int]] = []
    for index, option in enumerate(options):
        if index in correct:
            continue
        key = _SPACE.sub(" ", option.casefold())[:RATIONALE_KEY_LENGTH]
        position = folded.find(key)
        if position >= 0:
            found.append((position, index, len(key)))
    found.sort()
    rationales: dict[int, str] = {}
    for n, (position, index, key_length) in enumerate(found):
        end = found[n + 1][0] if n + 1 < len(found) else len(text)
        why = _LEADING_DASH.sub("", text[position + key_length : end]).strip()
        if why:
            rationales[index] = why
    return rationales


def _references(lines: list[str]) -> list[str]:
    refs: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(("http://", "https://")):
            refs.append(stripped)
        elif stripped and refs:
            refs[-1] += stripped  # a URL wrapped onto the next line
    return refs


def _parse_block(lines: list[str], group: str) -> ParsedQuestion | None:
    explanation_at = next(
        (i for i, line in enumerate(lines) if line.strip() == "Explanation"), len(lines)
    )
    body, tail = lines[:explanation_at], lines[explanation_at + 1 :]
    refs_at = next((i for i, line in enumerate(tail) if line.strip() == "References:"), len(tail))
    explanation, ref_lines = tail[:refs_at], tail[refs_at + 1 :]
    incorrect_at = next(
        (i for i, line in enumerate(explanation) if line.strip() == "Incorrect options:"),
        len(explanation),
    )
    correct_text = _norm(explanation[:incorrect_at])
    incorrect_text = _norm(explanation[incorrect_at + 1 :])

    paragraphs = _paragraphs(body)
    if not paragraphs:
        return None
    stem_lines, first_option = _split_stem(paragraphs[0], _norm(explanation).casefold())
    options, correct = _options(([first_option] if first_option else []) + paragraphs[1:])
    if not options:
        return None
    return ParsedQuestion(
        stem=_norm(stem_lines),
        options=options,
        correct=sorted(correct),
        explanation=correct_text,
        rationales=_rationales(options, correct, incorrect_text),
        references=_references(ref_lines),
        group=group,
    )


def parse_results_text(text: str, *, group: str = "") -> list[ParsedQuestion]:
    """Every question that has a body; a header with nothing under it is dropped."""
    questions: list[ParsedQuestion] = []
    block: list[str] | None = None
    for raw in text.replace("\f", "").splitlines():
        if _HEADER.match(raw.strip()):
            if block is not None and (parsed := _parse_block(block, group)):
                questions.append(parsed)
            block = []
        elif block is not None:
            block.append(raw)
    if block is not None and (parsed := _parse_block(block, group)):
        questions.append(parsed)
    return questions
