"""Subtitle tracks (SRT, WebVTT) to readable transcript text. Pure functions."""

from __future__ import annotations

import html
import re

_TIMING = re.compile(r"\d{1,2}:\d{2}(?::\d{2})?[.,]\d{3}\s*-->\s*\d{1,2}:\d{2}(?::\d{2})?[.,]\d{3}")
_CUE_INDEX = re.compile(r"^\d+$")
_TAG = re.compile(r"<[^>]+>")
_HEADER = re.compile(r"^(WEBVTT|NOTE\b|STYLE\b|REGION\b|Kind:|Language:)", re.IGNORECASE)
_SPEAKER_MARK = re.compile(r"^-?\s*>>\s*")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")

SENTENCES_PER_PARAGRAPH = 6


def caption_lines(text: str) -> list[str]:
    """The spoken lines of an SRT or WebVTT file in order, timing and markup removed.

    A line identical to the previous one is dropped: roll-up captions repeat the last
    cue, and some exports emit every cue twice.
    """
    lines: list[str] = []
    for raw in text.replace("﻿", "").splitlines():
        line = _TAG.sub("", raw).strip()
        if not line or _CUE_INDEX.match(line) or _TIMING.search(line) or _HEADER.match(line):
            continue
        line = html.unescape(_SPEAKER_MARK.sub("", line)).strip()
        if line and (not lines or line != lines[-1]):
            lines.append(line)
    return lines


def srt_to_vtt(text: str) -> str:
    """An SRT track as WebVTT for the browser's `<track>`: header, dotted timings, no indexes."""
    out = ["WEBVTT", ""]
    for raw in text.replace("﻿", "").splitlines():
        line = raw.rstrip("\r")
        if _TIMING.search(line):
            out.append(line.replace(",", "."))
        elif _CUE_INDEX.match(line.strip()):
            continue
        else:
            out.append(line)
    return "\n".join(out).rstrip() + "\n"


def caption_text(text: str) -> str:
    """Cues joined back into sentences, then grouped into short paragraphs.

    Subtitle cues break mid-sentence, so the lines are first joined with spaces and
    re-split on sentence ends; a paragraph break every few sentences keeps the result
    readable without pretending to know where the speaker paused.
    """
    stream = " ".join(caption_lines(text))
    sentences = [s.strip() for s in _SENTENCE_END.split(stream) if s.strip()]
    paragraphs = [
        " ".join(sentences[i : i + SENTENCES_PER_PARAGRAPH])
        for i in range(0, len(sentences), SENTENCES_PER_PARAGRAPH)
    ]
    return "\n\n".join(paragraphs)
