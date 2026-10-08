"""A course directory becomes a Markdown corpus with a manifest; the source is untouched."""

from __future__ import annotations

import json
from pathlib import Path

from app.corpus.ingest import infer_exam, ingest_course, ingest_tree, slugify

SRT = "1\n00:00:01,000 --> 00:00:02,000\n" + " ".join(f"word{i}" for i in range(40)) + "\n"


def test_exam_inference_from_course_names() -> None:
    hint = infer_exam("Ultimate AWS Certified SysOps Administrator Associate 2021 [SOA-C02]")
    assert (hint.code, hint.year) == ("SOA-C02", 2021)
    assert infer_exam("Certified Kubernetes Administrator (CKA), 3rd Edition").code == "CKA"
    assert infer_exam("AWS Cookbook") == infer_exam("x") and infer_exam("x").code is None
    assert slugify("10 - Docker Containers & ECS!") == "10-docker-containers-ecs"


def test_ingest_writes_markdown_manifest_and_skips_noise(tmp_path: Path) -> None:
    src = tmp_path / "Some Course 2022 [SAA-C03]"
    section = src / "03 - EC2"
    section.mkdir(parents=True)
    (section / "001 Intro_en.srt").write_text(SRT, encoding="utf-8")
    (section / "001 Intro_en.vtt").write_text("WEBVTT\n\n00:01.000 --> 00:02.000\nduplicate\n")
    (section / "002 Lesson Web Page.txt").write_text("https://example.com/only-a-link\n")
    (section / "Visit For More Courses.url").write_text("[InternetShortcut]\n")
    (section / "003 Lecture.mp4").write_bytes(b"\x00" * 16)
    before = sorted(p.name for p in section.iterdir())

    report = ingest_course(src, tmp_path / "corpus")

    assert sorted(p.name for p in section.iterdir()) == before, "the source is never modified"
    assert report.counts() == {"written": 1, "skipped": 4, "words": 40}
    written = report.out_dir / "03-ec2" / "001-intro-en.md"
    assert written.read_text(encoding="utf-8").startswith(
        "---\nsource: 03 - EC2/001 Intro_en.srt\nkind: srt\nwords: 40\n---\n\nword0 word1"
    )
    manifest = json.loads((report.out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["exam"] == {"code": "SAA-C03", "year": 2022}
    reasons = {entry["source"]: entry["reason"] for entry in manifest["skipped"]}
    assert reasons["03 - EC2/001 Intro_en.vtt"].startswith("duplicate of")
    assert reasons["03 - EC2/002 Lesson Web Page.txt"] == "too short"
    assert reasons["03 - EC2/Visit For More Courses.url"] == "not course text"
    assert reasons["03 - EC2/003 Lecture.mp4"] == "not course text"


def test_ingest_tree_treats_each_child_as_a_course(tmp_path: Path) -> None:
    topic = tmp_path / "AWS"
    (topic / "Course A").mkdir(parents=True)
    (topic / "Course A" / "001 Intro.srt").write_text(SRT, encoding="utf-8")
    (topic / "Course B [SOA-C02]").mkdir()
    (topic / "Course B [SOA-C02]" / "notes.md").write_text(
        " ".join(["note"] * 20), encoding="utf-8"
    )
    (topic / "Loose Notes.txt").write_text(" ".join(["loose"] * 30), encoding="utf-8")
    (topic / "Downloaded From Somewhere.txt").write_text(" ".join(["ad"] * 30), encoding="utf-8")
    (topic / "video.mp4").write_bytes(b"\x00")

    reports = ingest_tree(topic, tmp_path / "corpus")

    assert [r.course for r in reports] == ["Course A", "Course B [SOA-C02]", "Loose Notes"]
    assert [r.counts()["written"] for r in reports] == [1, 1, 1]
    assert (tmp_path / "corpus" / "loose-notes" / "loose-notes.md").exists()
    assert (tmp_path / "corpus" / "course-b-soa-c02" / "manifest.json").exists()
