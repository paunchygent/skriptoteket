"""Unit tests for the pytest native-library wrapper.

Purpose:
    Lock the local pytest command surface that makes WeasyPrint-backed PDF
    renderer tests deterministic on macOS package-manager installations.
Relationships:
    - Exercises `scripts.run_pytest_with_native_libs`.
    - Verifies native library environment assembly without importing
      WeasyPrint or spawning real renderer work.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from scripts import run_pytest_with_native_libs as module


def test_build_pytest_environment_preserves_non_macos_environment(monkeypatch) -> None:
    monkeypatch.setattr(module.sys, "platform", "linux")

    env = module.build_pytest_environment({"EXISTING": "1"})

    assert env == {"EXISTING": "1"}


def test_build_pytest_environment_adds_configured_macos_library_dirs(
    monkeypatch,
    tmp_path: Path,
) -> None:
    native_dir = tmp_path / "native-libs"
    native_dir.mkdir()
    monkeypatch.setattr(module.sys, "platform", "darwin")

    env = module.build_pytest_environment(
        {
            module.CONFIGURED_LIBRARY_DIRS_ENV: str(native_dir),
            "DYLD_FALLBACK_LIBRARY_PATH": "/already/there",
        }
    )

    expected_fallback = os.pathsep.join((str(native_dir), "/already/there"))
    assert env["DYLD_FALLBACK_LIBRARY_PATH"] == expected_fallback
    assert env["DYLD_LIBRARY_PATH"] == str(native_dir)


def test_main_executes_pytest_with_wrapped_environment(monkeypatch) -> None:
    subprocess_calls: list[tuple[list[str], bool, dict[str, str]]] = []

    class _Completed:
        returncode = 7

    def _fake_run(command: list[str], check: bool, env: dict[str, str]) -> _Completed:
        subprocess_calls.append((command, check, env))
        return _Completed()

    monkeypatch.setattr(module.subprocess, "run", _fake_run)
    monkeypatch.setattr(module, "build_pytest_environment", lambda: {"WRAPPED": "1"})

    result = module.main(["tests/unit"])

    assert result == 7
    assert subprocess_calls == [
        ([sys.executable, "-m", "pytest", "tests/unit"], False, {"WRAPPED": "1"})
    ]
