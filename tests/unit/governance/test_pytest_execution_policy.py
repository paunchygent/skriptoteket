"""Backend pytest runs parallel and quiet unless a serial run states why."""

from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

from tests.conftest import auto_worker_count, file_weight

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

    assert addopts[:4] == ["-n", "logical", "--dist", "worksteal"]
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


@pytest.mark.parametrize(
    ("file_count", "max_workers", "expected"),
    [
        (0, 24, 0),
        (1, 24, 0),
        (11, 24, 0),
        (12, 24, 2),
        (45, 24, 7),
        (133, 24, 22),
        (686, 24, 24),
        (686, 12, 12),
        (12, 1, 2),
    ],
)
def test_worker_count_follows_the_selection(
    file_count: int, max_workers: int, expected: int
) -> None:
    assert auto_worker_count(file_count, max_workers) == expected


def test_a_small_selection_runs_in_process_without_a_serial_reason() -> None:
    completed = _run_pytest()

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "created:" not in completed.stdout


def test_a_file_counts_as_its_declared_weight(tmp_path: Path) -> None:
    heavy = tmp_path / "test_heavy.py"
    heavy.write_text('# xdist-weight: 72 (a long sweep)\n"""Doc."""\n', encoding="utf-8")
    ordinary = tmp_path / "test_ordinary.py"
    ordinary.write_text('"""Doc."""\nVALUE = "# xdist-weight: 9"\n', encoding="utf-8")

    assert file_weight(heavy) == 72
    assert file_weight(ordinary) == 1
