"""Backend pytest runs parallel and quiet unless a serial run states why."""

from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

from tests.conftest import MAX_WORKERS, auto_worker_count, file_weight, selected_test_files

ROOT = Path(__file__).resolve().parents[3]
SMALL_TARGET = "tests/unit/domain/curated_apps/test_models.py"
USAGE_ERROR = 4
PYARGS_PACKAGE = "tests.unit.web.apps.classroom_planner"


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


@pytest.mark.parametrize(
    "worker_args",
    [("-n", "-1"), ("-n", "2", "--maxprocesses=-1")],
    ids=["negative-n", "negative-maxprocesses"],
)
def test_a_negative_worker_setting_is_refused(worker_args: tuple[str, ...]) -> None:
    completed = _run_pytest(*worker_args)

    assert completed.returncode == USAGE_ERROR, completed.stdout + completed.stderr
    assert "negative" in completed.stderr


def test_an_explicit_worker_count_above_the_cap_is_refused() -> None:
    completed = _run_pytest("-n", str(MAX_WORKERS + 1))

    assert completed.returncode == USAGE_ERROR, completed.stdout + completed.stderr
    assert f"at most {MAX_WORKERS} workers" in completed.stderr


def test_a_dotted_package_is_sized_by_its_files() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-p",
            "no:cacheprovider",
            "--pyargs",
            PYARGS_PACKAGE,
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "created: 2/2 workers" in completed.stdout


def test_a_missing_path_is_reported_instead_of_running_nothing_on_workers() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "tests/unit/no_such_file.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == USAGE_ERROR, completed.stdout + completed.stderr
    assert "file or directory not found: tests/unit/no_such_file.py" in completed.stderr


def test_a_selection_that_names_no_test_file_cannot_be_counted() -> None:
    assert selected_test_files(["tests.unit.no_such_package"], base=ROOT, pyargs=True) is None
    assert selected_test_files(["tests/unit/no_such_dir"], base=ROOT, pyargs=False) is None


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
