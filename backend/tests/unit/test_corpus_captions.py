"""Caption tracks become readable text: timing, indexes, tags and repeats removed."""

from __future__ import annotations

from app.corpus.captions import caption_lines, caption_text

SRT = """1
00:00:05,890 --> 00:00:11,530
In this exam cram, we're going to cover Docker containers and ECS. So, the key

2
00:00:11,530 --> 00:00:17,890
features are serverless computing with <i>AWS Fargate</i> &amp; scaling.

3
00:00:17,890 --> 00:00:21,040
features are serverless computing with AWS Fargate & scaling.
"""

VTT = """WEBVTT
Kind: captions
Language: en

NOTE this is a comment

00:03.990 --> 00:05.280
>> Good morning, my dear students.

00:05.280 --> 00:08.490
Welcome to the fourth session! The topic is reliability.
"""


def test_srt_lines_drop_timing_tags_and_repeats() -> None:
    assert caption_lines(SRT) == [
        "In this exam cram, we're going to cover Docker containers and ECS. So, the key",
        "features are serverless computing with AWS Fargate & scaling.",
    ]


def test_vtt_lines_drop_header_notes_and_speaker_marks() -> None:
    assert caption_lines(VTT) == [
        "Good morning, my dear students.",
        "Welcome to the fourth session! The topic is reliability.",
    ]


def test_text_joins_cues_into_sentences() -> None:
    text = caption_text(SRT)
    assert "the key features are serverless computing" in text
    assert "\n" not in text  # three sentences, one paragraph
    long = caption_text(
        "\n".join(f"{i}\n00:00:0{i % 10},000 --> 00:00:09,000\nSentence {i}." for i in range(14))
    )
    assert long.count("\n\n") == 2  # 14 sentences, six per paragraph
