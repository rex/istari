"""Whisper transcription: which lectures need it, how the backends are called, what is written."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import pytest

from app.corpus.transcribe import (
    Backend,
    detect_backend,
    ffmpeg_argv,
    pending_jobs,
    transcribe_course,
    transcribe_tree,
)

VIDEO = bytes(range(256))
VTT = "WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nhello\n"


def _course(root: Path, name: str = "Some Course 2024 [SAA-C03]") -> Path:
    course = root / name
    (course / "01 - Intro").mkdir(parents=True)
    (course / "01 - Intro" / "001 Welcome.mp4").write_bytes(VIDEO)
    (course / "01 - Intro" / "001 Welcome.srt").write_text("1\n00:00:00,000 --> 00:00:01,000\nhi\n")
    (course / "01 - Intro" / "002 Setup.mp4").write_bytes(VIDEO)
    (course / "02 - IAM").mkdir()
    (course / "02 - IAM" / "001 Roles.mp4").write_bytes(VIDEO)
    return course


def _fake_run(calls: list[list[str]]):  # type: ignore[no-untyped-def]
    def run(argv: Sequence[str]) -> None:
        calls.append(list(argv))
        if argv[0] == "ffmpeg":
            Path(argv[-1]).write_bytes(b"RIFF")
        else:
            out_stem = (
                Path(argv[argv.index("-of") + 1])
                if "-of" in argv
                else Path(argv[1]).with_suffix("")
            )
            out_stem.with_suffix(".vtt").write_text(VTT, encoding="utf-8")

    return run


def test_pending_jobs_skip_captioned_lectures_and_written_targets(tmp_path: Path) -> None:
    course = _course(tmp_path)
    jobs = pending_jobs(course)
    assert [job.relative for job in jobs] == ["01 - Intro/002 Setup.mp4", "02 - IAM/001 Roles.mp4"]
    assert jobs[0].target == course / "01 - Intro" / "002 Setup.vtt"
    corpus = pending_jobs(course, tmp_path / "out")
    assert corpus[1].target == tmp_path / "out" / "02 - IAM" / "001 Roles.vtt"
    # A caption written beside the video, by anyone, takes the lecture off the list.
    (course / "02 - IAM" / "001 Roles.vtt").write_text(VTT)
    assert [job.relative for job in pending_jobs(course)] == ["01 - Intro/002 Setup.mp4"]
    assert [job.relative for job in pending_jobs(course, tmp_path / "out")] == [
        "01 - Intro/002 Setup.mp4"
    ]


def test_detect_backend_prefers_whisper_cpp_and_names_its_model_file(tmp_path: Path) -> None:
    cpp = detect_backend(
        "large-v3-turbo",
        model_dir=tmp_path,
        which=lambda name: "/opt/bin/whisper-cli" if name == "whisper-cli" else None,
    )
    assert (cpp.name, cpp.model_path) == ("cpp", tmp_path / "ggml-large-v3-turbo.bin")
    work = tmp_path / "work"
    argv = cpp.argv(work / "a.wav", work / "a")
    assert argv[:3] == ["/opt/bin/whisper-cli", "-m", str(tmp_path / "ggml-large-v3-turbo.bin")]
    assert "-ovtt" in argv and argv[argv.index("-of") + 1] == str(work / "a")

    openai = detect_backend(
        "small.en", which=lambda name: "/opt/bin/whisper" if name == "whisper" else None
    )
    assert (openai.name, openai.model_path) == ("openai", None)
    assert openai.argv(work / "a.wav", work / "a")[-5:] == [
        "vtt",
        "--output_dir",
        str(work),
        "--verbose",
        "False",
    ]

    # parakeet-mlx wins the automatic choice and brings its own default model.
    installed = {"parakeet-mlx": "/opt/bin/parakeet-mlx", "whisper-cli": "/opt/bin/whisper-cli"}
    parakeet = detect_backend(which=installed.get)
    assert (parakeet.name, parakeet.model) == ("parakeet", "mlx-community/parakeet-tdt-0.6b-v3")
    assert parakeet.argv(work / "a.wav", work / "a")[-4:] == [
        "--output-format",
        "vtt",
        "--output-dir",
        str(work),
    ]
    assert detect_backend(preferred="cpp", which=installed.get).model == "large-v3-turbo"
    with pytest.raises(FileNotFoundError):
        detect_backend(which=lambda name: None)
    assert ffmpeg_argv(Path("v.mp4"), Path("a.wav"))[-5:] == ["-ar", "16000", "-f", "wav", "a.wav"]


def test_transcribe_course_writes_next_to_the_video_and_a_manifest(tmp_path: Path) -> None:
    course = _course(tmp_path)
    calls: list[list[str]] = []
    backend = Backend("cpp", "whisper-cli", "large-v3-turbo", tmp_path / "ggml.bin")
    report = transcribe_course(course, backend, run=_fake_run(calls), log=lambda _: None)
    assert report.done == ["01 - Intro/002 Setup.mp4", "02 - IAM/001 Roles.mp4"]
    assert report.skipped == 1 and report.failed == []
    assert (course / "02 - IAM" / "001 Roles.vtt").read_text(encoding="utf-8") == VTT
    manifest = json.loads((course / ".istari-captions.json").read_text(encoding="utf-8"))
    assert manifest["model"] == "large-v3-turbo" and manifest["backend"] == "cpp"
    assert set(manifest["files"]) == set(report.done)
    assert calls[0][0] == "ffmpeg" and calls[1][0] == "whisper-cli"

    # Resumable: nothing left to do, nothing re-run.
    again = transcribe_course(course, backend, run=_fake_run(calls), log=lambda _: None)
    assert again.done == [] and again.skipped == 3 and len(calls) == 4


def test_transcribe_tree_lands_under_the_corpus_and_honours_the_limit(tmp_path: Path) -> None:
    root = tmp_path / "Cloud" / "AWS"
    _course(root)
    calls: list[list[str]] = []
    backend = Backend("openai", "whisper", "small.en")
    reports = transcribe_tree(
        root,
        backend,
        out_root=tmp_path / "corpus",
        limit=1,
        run=_fake_run(calls),
        log=lambda _: None,
    )
    assert [r.done for r in reports] == [["01 - Intro/002 Setup.mp4"]]
    captions = tmp_path / "corpus" / "some-course-2024-saa-c03" / "captions"
    assert (captions / "01 - Intro" / "002 Setup.vtt").is_file()
    assert (
        "01 - Intro/002 Setup.mp4" in json.loads((captions / "manifest.json").read_text())["files"]
    )


def test_a_failed_lecture_is_reported_and_the_rest_continue(tmp_path: Path) -> None:
    course = _course(tmp_path)

    def run(argv: Sequence[str]) -> None:
        if argv[0] == "ffmpeg" and "002 Setup" in argv[5]:
            raise OSError("ffmpeg: broken file")
        _fake_run([])(argv)

    report = transcribe_course(
        course, Backend("cpp", "whisper-cli", "m", tmp_path / "m.bin"), run=run, log=lambda _: None
    )
    assert [relative for relative, _ in report.failed] == ["01 - Intro/002 Setup.mp4"]
    assert report.done == ["02 - IAM/001 Roles.mp4"]
