import os
import re
from collections.abc import Iterable
from pathlib import Path

import pytest

from tests.fixtures.identity_fixtures import now

__all__ = ["now"]

SERIAL_REASON_OPTION = "--serial-reason"
_SERIAL_REASON_KEY = pytest.StashKey[str]()
_SIZED_SERIAL_KEY = pytest.StashKey[bool]()


def selected_test_files(args: Iterable[str]) -> frozenset[Path]:
    """The test files a run's path arguments select (a directory selects every file in it)."""

    files: set[Path] = set()
    for arg in args:
        path = Path(arg.split("::", 1)[0])
        if path.is_dir():
            files.update(path.rglob("test_*.py"))
            files.update(path.rglob("*_test.py"))
        elif path.is_file():
            files.add(path)
    return frozenset(files)


SERIAL_BELOW_FILES = 12
FILES_PER_WORKER = 6
_WEIGHT_COMMENT = re.compile(r"^# xdist-weight: (\d+)\b", re.MULTILINE)
_WEIGHT_SCAN_BYTES = 4096


def file_weight(path: Path) -> int:
    """How many ordinary files one test file counts as when workers are sized.

    A file whose tests together take minutes (a parametrized sweep) declares
    ``# xdist-weight: <n>`` near its top; every other file counts as one. The comment is read
    as text, so sizing never imports a module.
    """

    with path.open("rb") as handle:
        head = handle.read(_WEIGHT_SCAN_BYTES).decode("utf-8", errors="replace")
    match = _WEIGHT_COMMENT.search(head)
    return int(match.group(1)) if match else 1


def auto_worker_count(file_count: int, max_workers: int) -> int:
    """Workers for a run that selects ``file_count`` test files.

    Starting a worker costs about a second of CPU and every worker collects every selected
    module, while 10-15 agents run small focused runs on the same host. A run of fewer than
    SERIAL_BELOW_FILES files runs in-process; a larger run gets one worker per
    FILES_PER_WORKER files, at least two and at most ``max_workers``.
    """

    if file_count < SERIAL_BELOW_FILES:
        return 0
    return max(2, min(max_workers, file_count // FILES_PER_WORKER))


def pytest_xdist_auto_num_workers(config: pytest.Config) -> int:
    """Size `-n logical` (the addopts default) to the selection; hardware threads cap it."""

    weight = sum(file_weight(path) for path in selected_test_files(config.args))
    workers = auto_worker_count(weight, os.cpu_count() or 1)
    if workers == 0:
        config.stash[_SIZED_SERIAL_KEY] = True
    return workers


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        SERIAL_REASON_OPTION,
        default=None,
        help=(
            "Why this run is serial (-n 0). Required for every serial run; the default "
            "run is parallel. Valid reasons: pdb, or live output of one failing test."
        ),
    )


def pytest_configure(config: pytest.Config) -> None:
    """Refuse a serial run that does not state why it is serial."""

    if hasattr(config, "workerinput"):  # xdist worker: the controller already checked
        return
    if config.getoption("numprocesses", default=None):
        return
    if config.stash.get(_SIZED_SERIAL_KEY, False):  # one selected file: serial by design
        return
    reason = (config.getoption(SERIAL_REASON_OPTION) or "").strip()
    if not reason:
        raise pytest.UsageError(
            "This pytest run is serial (-n 0, --pdb, or addopts overridden). "
            "Backend tests run in parallel by default (a run that selects one file runs "
            "in-process on its own); drop the serial flag, or state why "
            f'it must be serial with {SERIAL_REASON_OPTION} "<reason>" '
            '(for example: pdm run test-serial --serial-reason "pdb on <test>" <test>).'
        )
    config.stash[_SERIAL_REASON_KEY] = reason


def pytest_report_header(config: pytest.Config) -> str | None:
    reason = config.stash.get(_SERIAL_REASON_KEY, None)
    return f"serial run: {reason}" if reason else None
