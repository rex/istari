"""Version, commit and build date of the running process, resolved once at startup.

Production images carry GIT_COMMIT and BUILD_DATE as environment variables (Docker
build args; see the Dockerfile and `make docker-build`). In development the commit
comes from `git rev-parse --short HEAD` and the build date stays unset. The values are
shown in the footer of every page and reported by `/api/health`.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

# backend/app/buildinfo.py -> the repository root in a checkout, `/` in the container
# (the Dockerfile copies VERSION there).
ROOT = Path(__file__).resolve().parents[2]
UNKNOWN = "unknown"
FALLBACK_VERSION = "0.0.0"


@dataclass(frozen=True, slots=True)
class BuildInfo:
    version: str
    commit: str
    built_at: str | None
    started_at: datetime


def read_version(root: Path = ROOT) -> str:
    path = root / "VERSION"
    if not path.is_file():
        return FALLBACK_VERSION
    return path.read_text(encoding="utf-8").strip() or FALLBACK_VERSION


def git_short_commit(root: Path = ROOT) -> str | None:
    """The checkout's HEAD, or None when git or the repository is absent (containers)."""
    git = shutil.which("git")
    if git is None or not (root / ".git").exists():
        return None
    try:
        result = subprocess.run(  # noqa: S603 - fixed argv, no user input
            [git, "rev-parse", "--short", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    commit = result.stdout.strip()
    return commit if result.returncode == 0 and commit else None


def load_build_info(
    *,
    commit: str = "",
    build_date: str = "",
    root: Path = ROOT,
    now: datetime | None = None,
) -> BuildInfo:
    """Environment values win; a git checkout fills the commit in during development."""
    return BuildInfo(
        version=read_version(root),
        commit=commit.strip() or git_short_commit(root) or UNKNOWN,
        built_at=build_date.strip() or None,
        started_at=now or datetime.now(UTC),
    )
