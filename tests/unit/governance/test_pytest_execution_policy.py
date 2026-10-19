"""Backend pytest runs parallel and quiet unless a serial run states why."""

from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SMALL_TARGET = "tests/unit/domain/curated_apps/test_models.py"
USAGE_ERROR = 4


def _run_pytest(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", *args, SMALL_TARGET],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_default_addopts_are_parallel_and_quiet() -> None:
    options = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["tool"][
        "pytest"
    ]["ini_options"]
    addopts = options["addopts"].split()

    assert addopts[:4] == ["-n", "auto", "--dist", "worksteal"]
    assert not {"-s", "-v", "-vv"} & set(addopts)
    assert not any(option.startswith("--log-cli") for option in addopts)
    assert "log_cli" not in options
    assert options["log_level"] == "INFO"


@pytest.mark.parametrize(
    "serial_args",
    [("-n", "0"), ("--pdb",), ("-o", "addopts=")],
    ids=["n0", "pdb", "addopts-override"],
)
def test_serial_run_without_reason_is_refused(serial_args: tuple[str, ...]) -> None:
    completed = _run_pytest(*serial_args)

    assert completed.returncode == USAGE_ERROR, completed.stdout + completed.stderr
    assert "--serial-reason" in completed.stderr


def test_serial_run_with_reason_runs_and_reports_the_reason() -> None:
    completed = _run_pytest("-n", "0", "--serial-reason", "live log of one test")

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "serial run: live log of one test" in completed.stdout


def test_blank_serial_reason_is_refused() -> None:
    completed = _run_pytest("-n", "0", "--serial-reason", "  ")

    assert completed.returncode == USAGE_ERROR
