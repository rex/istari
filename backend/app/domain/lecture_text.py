"""Transcript text as terms: the tokenizer and the document a lecture becomes. Pure."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass

STOPWORDS = frozenset(
    [
        "a",
        "about",
        "above",
        "after",
        "again",
        "against",
        "all",
        "am",
        "an",
        "and",
        "any",
        "are",
        "as",
        "at",
        "be",
        "because",
        "been",
        "before",
        "being",
        "below",
        "between",
        "both",
        "but",
        "by",
        "can",
        "could",
        "did",
        "do",
        "does",
        "doing",
        "down",
        "during",
        "each",
        "few",
        "for",
        "from",
        "further",
        "had",
        "has",
        "have",
        "having",
        "he",
        "her",
        "here",
        "hers",
        "herself",
        "him",
        "himself",
        "his",
        "how",
        "i",
        "if",
        "in",
        "into",
        "is",
        "it",
        "its",
        "itself",
        "just",
        "let",
        "me",
        "more",
        "most",
        "my",
        "myself",
        "no",
        "nor",
        "not",
        "now",
        "of",
        "off",
        "on",
        "once",
        "only",
        "or",
        "other",
        "our",
        "ours",
        "ourselves",
        "out",
        "over",
        "own",
        "same",
        "she",
        "should",
        "so",
        "some",
        "such",
        "than",
        "that",
        "the",
        "their",
        "theirs",
        "them",
        "themselves",
        "then",
        "there",
        "these",
        "they",
        "this",
        "those",
        "through",
        "to",
        "too",
        "under",
        "until",
        "up",
        "very",
        "was",
        "we",
        "were",
        "what",
        "when",
        "where",
        "which",
        "while",
        "who",
        "whom",
        "why",
        "will",
        "with",
        "would",
        "you",
        "your",
        "yours",
        "yourself",
        "yourselves",
        "um",
        "uh",
        "okay",
        "ok",
        "right",
        "yeah",
        "yes",
        "gonna",
        "wanna",
        "going",
        "get",
        "got",
        "go",
        "lot",
        "thing",
        "things",
        "really",
        "actually",
        "basically",
        "kind",
        "sort",
        "like",
        "one",
        "two",
        "three",
        "also",
        "well",
        "way",
        "see",
        "look",
        "want",
        "know",
        "think",
        "make",
        "need",
        "take",
        "use",
        "using",
        "used",
        "call",
        "called",
        "say",
        "said",
        "let",
        "lets",
        "us",
    ]
)

_TOKEN = re.compile(r"[a-z0-9][a-z0-9+.#-]*")


def _singular(token: str) -> str:
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def tokenize(text: str) -> list[str]:
    """Lowercase terms worth matching on: no stopwords, no bare numbers, plurals folded.
    Service names survive as one term ("s3", "ec2", "route-53", "node.js")."""
    terms: list[str] = []
    for raw in _TOKEN.findall(text.lower()):
        token = raw.strip(".-#+")
        if len(token) < 2 or token.isdigit() or token in STOPWORDS:
            continue
        terms.append(_singular(token))
    return terms


@dataclass(frozen=True, slots=True)
class Document:
    key: str
    terms: Mapping[str, int]
    length: int


def document(key: str, text: str) -> Document:
    counts = Counter(tokenize(text))
    return Document(key=key, terms=dict(counts), length=sum(counts.values()))
