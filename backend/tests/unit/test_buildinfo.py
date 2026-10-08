"""Build info resolution: environment wins, the checkout fills in during development."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.buildinfo import ROOT, UNKNOWN, git_short_commit, load_build_info, read_version


def test_environment_values_win_over_the_checkout(tmp_path: Path) -> None:
    (tmp_path / "VERSION").write_text("9.8.7\n", encoding="utf-8")
    now = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)
    info = load_build_info(
        commit=" abc1234 ", build_date="2026-10-07T00:00:00Z", root=tmp_path, now=now
    )
    assert (info.version, info.commit, info.built_at) == (
        "9.8.7",
        "abc1234",
        "2026-10-07T00:00:00Z",
    )
    assert info.started_at == now


def test_outside_a_checkout_everything_falls_back(tmp_path: Path) -> None:
    info = load_build_info(root=tmp_path)
    assert info.version == "0.0.0"
    assert info.commit == UNKNOWN
    assert info.built_at is None
    assert info.started_at.tzinfo is not None


def test_the_checkout_supplies_version_and_commit() -> None:
    if not (ROOT / ".git").exists():
        pytest.skip("not running inside a git checkout")
    commit = git_short_commit()
    assert commit is not None and len(commit) >= 7
    int(commit, 16)  # a hex short hash, never a branch name or an error message
    assert read_version() == (ROOT / "VERSION").read_text(encoding="utf-8").strip()
