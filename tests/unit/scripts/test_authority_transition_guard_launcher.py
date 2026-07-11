"""Contract tests for the Skriptoteket shared authority-guard adapter."""

from __future__ import annotations

import subprocess
from pathlib import Path

from scripts import validate_docs


def test_authority_validation_uses_canonical_launcher_and_explicit_root(monkeypatch) -> None:
    captured: list[tuple[list[str], Path]] = []

    def fake_run(command, *, cwd, check, text, capture_output):
        captured.append((command, cwd))
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(validate_docs.subprocess, "run", fake_run)
    result = validate_docs.validate_authority_transitions(
        [Path("docs") / "with space.md"],
        scoped=True,
    )

    assert result == []
    launcher = (
        Path.home()
        / ".codex/skill-repository/scripts/docs_as_code/run_authority_transition_guard.sh"
    )
    assert captured == [
        (
            [str(launcher), "--repo-root", str(validate_docs.ROOT), "docs/with space.md"],
            validate_docs.ROOT,
        )
    ]


def test_authority_validation_propagates_child_failure(monkeypatch) -> None:
    def fake_run(command, *, cwd, check, text, capture_output):
        return subprocess.CompletedProcess(command, 9, "shared failure", "")

    monkeypatch.setattr(validate_docs.subprocess, "run", fake_run)
    assert validate_docs.validate_authority_transitions([], scoped=False) == [
        validate_docs.Violation("docs", "shared failure")
    ]
