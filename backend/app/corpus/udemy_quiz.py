"""Parse a Udemy section quiz saved as HTML (the accordion export) into questions.

The export is one fixed template: a panel per question whose title holds the stem,
numbered badges for the options, a "Correct Answer" panel listing the right badge
numbers, then an "Explanation" alert. Parsing is by regular expressions on that
template, not a general HTML parser, and it is tested against a synthetic copy of
the shape.
"""

from __future__ import annotations

import html
import re

from app.corpus.private_pack import ParsedQuestion

_QUESTION = re.compile(
    r'href="#question(?P<n>\d+)">\s*Question\s*(?P=n)\s*</a>(?P<body>.*?)'
    r'(?=href="#question\d+">\s*Question\s*\d+\s*</a>|</body>|$)',
    re.S,
)
_STEM = re.compile(r'<h4 class="panel-title">\s*(?:<p>)?(?P<stem>.*?)(?:</p>)?\s*</h4>', re.S)
_OPTION = re.compile(
    r'<span class="badge"[^>]*>\s*(?P<n>\d+)\s*</span>\s*<label>\s*<input[^>]*>\s*(?P<text>.*?)'
    r"</label>",
    re.S,
)
# Everything after the answer panel opens: its badges are the correct numbers, and the
# explanation that may follow carries no badges. Some exports have no explanation at all.
_ANSWER_PANEL = re.compile(r'id="answer\d+"(?P<body>.*)', re.S)
_ANSWER_PANEL_WITH_EXPLANATION = re.compile(
    r'id="answer\d+".*?<div class="panel-body">(?P<body>.*?)<div class="alert"', re.S
)
_ANSWER_BADGE = re.compile(r'<span class="badge"[^>]*>\s*(?P<n>\d+)\s*</span>')
_EXPLANATION = re.compile(
    r"Explanation\s*</strong>.*?<div class=\"alert\"[^>]*>(?P<text>.*?)</div>", re.S
)
_TAG = re.compile(r"<[^>]+>")
_SPACE = re.compile(r"[ \t]+")


def clean(fragment: str) -> str:
    """Markup to text: paragraph breaks kept, other tags dropped, entities decoded."""
    text = re.sub(r"</p>\s*<p>", "\n\n", fragment)
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = _TAG.sub("", text)
    text = html.unescape(text)
    lines = [_SPACE.sub(" ", line).strip() for line in text.splitlines()]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def parse_quiz_html(document: str, *, group: str = "") -> list[ParsedQuestion]:
    questions: list[ParsedQuestion] = []
    for match in _QUESTION.finditer(document):
        body = match.group("body")
        stem_match = _STEM.search(body)
        options = [clean(m.group("text")) for m in _OPTION.finditer(body)]
        answer = _ANSWER_PANEL.search(body)
        correct = (
            sorted({int(m.group("n")) - 1 for m in _ANSWER_BADGE.finditer(answer.group("body"))})
            if answer
            else []
        )
        explanation_match = _EXPLANATION.search(body)
        questions.append(
            ParsedQuestion(
                stem=clean(stem_match.group("stem")) if stem_match else "",
                options=options,
                correct=[i for i in correct if 0 <= i < len(options)],
                explanation=clean(explanation_match.group("text")) if explanation_match else "",
                group=group,
            )
        )
    return questions
