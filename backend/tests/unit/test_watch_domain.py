"""Naming and caption rules for the course player, and SRT to WebVTT."""

from __future__ import annotations

from app.corpus.captions import srt_to_vtt
from app.domain.naming import natural_key
from app.domain.watch import caption_for, course_slug, lecture_title, section_title

SRT = (
    "﻿1\r\n00:00:05,890 --> 00:00:11,530\r\nIn this exam cram, we cover ECS.\r\n\r\n"
    "2\r\n00:00:11,530 --> 00:00:17,890\r\nFargate, managed for you.\r\n"
)


def test_natural_order_puts_two_before_ten() -> None:
    names = ["10 - VPC", "2 - IAM", "1 - Intro", "02 - IAM copy", "Appendix"]
    assert sorted(names, key=natural_key) == [
        "1 - Intro",
        "2 - IAM",
        "02 - IAM copy",
        "10 - VPC",
        "Appendix",
    ]


def test_lecture_and_section_titles_drop_numbering_and_underscores() -> None:
    assert lecture_title("012 Amazon Elastic Container Registry (ECR).mp4") == (
        "Amazon Elastic Container Registry (ECR)"
    )
    assert lecture_title("4 - Reliability_in_AWS.mp4") == "Reliability in AWS"
    assert lecture_title("007.mp4") == "007"
    assert section_title(".") == "Lectures" and section_title("03 - EC2/labs") == "03 - EC2 / labs"


def test_course_slug_is_readable_stable_and_unique_per_location() -> None:
    a = course_slug("Cloud/AWS", "AWS Certified Solutions Architect Associate Training SAA-C03")
    assert a == course_slug(
        "Cloud/AWS", "AWS Certified Solutions Architect Associate Training SAA-C03"
    )
    assert a.startswith("aws-certified-solutions-architect-associate-training-saa-c03-")
    assert a != course_slug(
        "Cloud/Azure", "AWS Certified Solutions Architect Associate Training SAA-C03"
    )


def test_caption_matching_prefers_vtt_and_exact_stems_then_prefix_variants() -> None:
    siblings = {
        f.lower(): f
        for f in [
            "001 Intro.mp4",
            "001 Intro_en.srt",
            "001 Intro.vtt",
            "4 - Reliability.mp4",
            "4 - Reliability English.vtt",
            "9 - Alone.mp4",
        ]
    }
    assert caption_for("001 Intro", siblings) == "001 Intro.vtt"
    del siblings["001 intro.vtt"]
    assert caption_for("001 Intro", siblings) == "001 Intro_en.srt"
    assert caption_for("4 - Reliability", siblings) == "4 - Reliability English.vtt"
    assert caption_for("9 - Alone", siblings) is None


def test_srt_to_vtt_adds_header_dots_timings_and_drops_indexes() -> None:
    vtt = srt_to_vtt(SRT)
    assert vtt.startswith("WEBVTT\n\n")
    assert "00:00:05.890 --> 00:00:11.530\nIn this exam cram, we cover ECS." in vtt
    assert "\n1\n" not in vtt and "," not in vtt.split("\n")[2]
    assert vtt.endswith("Fargate, managed for you.\n")
