"""Transcribe lectures that have no captions into WebVTT with Whisper.

Two backends: whisper.cpp (`whisper-cli`; Metal on Apple silicon, the fast one) and the
openai-whisper CLI (`whisper`). Output goes next to the video (on the share, where every
player and the catalog find it) or under a corpus directory. A manifest records the model,
the backend and the date per file, so a generated transcript is never mistaken for a
publisher's. Idempotent and resumable: a lecture with any caption sibling, or whose target
already exists, is skipped, and the manifest is rewritten after every file.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.domain.naming import is_junk_name, natural_key, slugify
from app.domain.watch import VIDEO_SUFFIXES, caption_for

DEFAULT_MODEL = "large-v3-turbo"
# What each backend transcribes with when no model is named: Parakeet TDT 0.6B v3 is the
# fast, English-first MLX model; the Whisper backends take a Whisper model name.
DEFAULT_MODELS = {
    "parakeet": "mlx-community/parakeet-tdt-0.6b-v3",
    "cpp": DEFAULT_MODEL,
    "openai": DEFAULT_MODEL,
}
SHARE_MANIFEST = ".istari-captions.json"
CORPUS_MANIFEST = "manifest.json"
_CPP_EXECUTABLES = ("whisper-cli", "whisper-cpp")

Runner = Callable[[Sequence[str]], None]


@dataclass(frozen=True, slots=True)
class Job:
    video: Path
    relative: str
    target: Path


@dataclass(frozen=True, slots=True)
class Backend:
    """How to call Whisper: the executable, the model, and whisper.cpp's model file."""

    name: str
    executable: str
    model: str
    model_path: Path | None = None

    def argv(self, audio: Path, out_stem: Path) -> list[str]:
        """Every backend leaves `<out_stem>.vtt` behind when the audio is named after it."""
        if self.name == "parakeet":
            return [
                self.executable,
                str(audio),
                "--model",
                self.model,
                "--output-format",
                "vtt",
                "--output-dir",
                str(out_stem.parent),
            ]
        if self.name == "cpp":
            return [
                self.executable,
                "-m",
                str(self.model_path),
                "-f",
                str(audio),
                "-l",
                "en",
                "-ovtt",
                "-of",
                str(out_stem),
                "-np",
            ]
        return [
            self.executable,
            str(audio),
            "--model",
            self.model,
            "--language",
            "en",
            "--output_format",
            "vtt",
            "--output_dir",
            str(out_stem.parent),
            "--verbose",
            "False",
        ]


@dataclass
class Report:
    course: str
    done: list[str] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)
    skipped: int = 0


def detect_backend(
    model: str | None = None,
    *,
    preferred: str = "auto",
    model_dir: Path | None = None,
    which: Callable[[str], str | None] = shutil.which,
) -> Backend:
    """The first installed backend in order of speed on a Mac: parakeet-mlx, whisper.cpp,
    openai-whisper; `preferred` names one. `model` None takes the backend's default."""
    if preferred in ("auto", "parakeet"):
        executable = which("parakeet-mlx")
        if executable:
            return Backend("parakeet", executable, model or DEFAULT_MODELS["parakeet"])
    if preferred in ("auto", "cpp"):
        for name in _CPP_EXECUTABLES:
            executable = which(name)
            if executable:
                chosen = model or DEFAULT_MODELS["cpp"]
                root = model_dir or Path.home() / ".cache" / "whisper.cpp"
                return Backend("cpp", executable, chosen, root / f"ggml-{chosen}.bin")
    if preferred in ("auto", "openai"):
        executable = which("whisper")
        if executable:
            return Backend("openai", executable, model or DEFAULT_MODELS["openai"])
    raise FileNotFoundError(
        "no transcription backend: install parakeet-mlx, whisper-cpp or openai-whisper, "
        "or pass --backend"
    )


def ffmpeg_argv(video: Path, wav: Path) -> list[str]:
    """Mono 16 kHz WAV, what both backends want."""
    return [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-i",
        str(video),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-f",
        "wav",
        str(wav),
    ]


def _videos(course_dir: Path) -> Iterator[tuple[Path, bool]]:
    """Every video under the course in course order, with whether a caption sits beside it."""
    for dirpath, dirnames, filenames in os.walk(course_dir):
        dirnames[:] = sorted(
            (d for d in dirnames if not d.startswith(".") and not is_junk_name(d)),
            key=natural_key,
        )
        siblings = {name.lower(): name for name in filenames}
        for name in sorted(filenames, key=natural_key):
            if Path(name).suffix.lower() in VIDEO_SUFFIXES:
                yield Path(dirpath) / name, caption_for(Path(name).stem, siblings) is not None


def pending_jobs(course_dir: Path, out_dir: Path | None = None) -> list[Job]:
    """Videos without a caption sibling whose target is not written yet, in course order;
    `out_dir` None means the VTT goes next to the video."""
    jobs: list[Job] = []
    for video, captioned in _videos(course_dir):
        if captioned:
            continue
        relative = video.relative_to(course_dir).as_posix()
        target = (
            video.with_suffix(".vtt")
            if out_dir is None
            else out_dir / Path(relative).with_suffix(".vtt")
        )
        if not target.exists():
            jobs.append(Job(video, relative, target))
    return jobs


def _manifest_path(course_dir: Path, out_dir: Path | None) -> Path:
    return course_dir / SHARE_MANIFEST if out_dir is None else out_dir / CORPUS_MANIFEST


def _load_manifest(path: Path) -> dict[str, Any]:
    if path.is_file():
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data.setdefault("files", {})
            return data
    return {"files": {}}


def _run_checked(argv: Sequence[str]) -> None:
    subprocess.run(list(argv), check=True, capture_output=True)  # noqa: S603 - fixed argv, no shell


def transcribe_course(
    course_dir: Path,
    backend: Backend,
    *,
    out_dir: Path | None = None,
    limit: int | None = None,
    run: Runner = _run_checked,
    log: Callable[[str], None] = print,
) -> Report:
    """Transcribe the uncaptioned lectures of one course; the manifest grows after each."""
    jobs = pending_jobs(course_dir, out_dir)
    report = Report(course=course_dir.name, skipped=sum(1 for _ in _videos(course_dir)) - len(jobs))
    manifest_path = _manifest_path(course_dir, out_dir)
    manifest = _load_manifest(manifest_path)
    for job in jobs[:limit]:
        started = time.monotonic()
        with tempfile.TemporaryDirectory(prefix="istari-whisper-") as tmp:
            stem = Path(tmp) / job.target.stem
            try:
                run(ffmpeg_argv(job.video, stem.with_suffix(".wav")))
                run(backend.argv(stem.with_suffix(".wav"), stem))
                produced = stem.with_suffix(".vtt")
                if not produced.is_file():
                    raise FileNotFoundError(f"{backend.name} wrote no VTT for {job.relative}")
                job.target.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(produced), str(job.target))
            except (OSError, subprocess.CalledProcessError) as exc:
                report.failed.append((job.relative, str(exc)[:300]))
                log(f"failed {job.relative}: {exc}")
                continue
        seconds = round(time.monotonic() - started, 1)
        manifest["files"][job.relative] = {
            "model": backend.model,
            "backend": backend.name,
            "generated_at": datetime.now(UTC).isoformat(),
            "seconds": seconds,
        }
        manifest["model"] = backend.model
        manifest["backend"] = backend.name
        manifest["updated_at"] = datetime.now(UTC).isoformat()
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        report.done.append(job.relative)
        log(f"{job.relative}: {seconds} s")
    return report


def transcribe_tree(
    root: Path,
    backend: Backend,
    *,
    out_root: Path | None = None,
    limit: int | None = None,
    run: Runner = _run_checked,
    log: Callable[[str], None] = print,
) -> list[Report]:
    """Every course directory under a topic folder; `limit` applies per course."""
    courses = sorted(
        (child for child in root.iterdir() if child.is_dir() and not child.name.startswith(".")),
        key=lambda child: natural_key(child.name),
    )
    return [
        transcribe_course(
            course,
            backend,
            out_dir=None if out_root is None else out_root / slugify(course.name) / "captions",
            limit=limit,
            run=run,
            log=log,
        )
        for course in courses
    ]
