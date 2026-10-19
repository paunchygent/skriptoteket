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


def selected_test_files(args: Iterable[str], *, base: Path, pyargs: bool) -> frozenset[Path] | None:
    """The test files a run's arguments select, or None when an argument names no test file.

    A directory selects every test file in it. With ``--pyargs`` a dotted name selects the
    package directory or module under ``base`` that it names. An argument this cannot resolve
    makes the selection uncountable, and sizing treats an uncountable run as a large one.
    """

    files: set[Path] = set()
    for arg in args:
        target = arg.split("::", 1)[0]
        path = base / target
        if not path.exists() and pyargs:
            dotted = base.joinpath(*target.split("."))
            path = dotted if dotted.is_dir() else dotted.with_suffix(".py")
        if path.is_dir():
            files.update(path.rglob("test_*.py"))
            files.update(path.rglob("*_test.py"))
        elif path.is_file():
            files.add(path)
        else:
            return None
    return frozenset(files)


# User decision 2026-10-19: 12 workers serve a full suite as fast as 24 under real load and
# leave room for the agents' concurrent small runs (TASK-SKRIPT-REP-0050 load table).
MAX_WORKERS = 12
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


def worker_cap() -> int:
    """The most workers any run may start: MAX_WORKERS, or fewer on a smaller host."""

    return min(MAX_WORKERS, os.cpu_count() or 1)


def pytest_xdist_auto_num_workers(config: pytest.Config) -> int:
    """Size `-n logical` (the addopts default) to the selection, capped at MAX_WORKERS."""

    files = selected_test_files(
        config.args, base=config.invocation_params.dir, pyargs=bool(config.option.pyargs)
    )
    if files is None:
        missing = [
            arg
            for arg in config.args
            if not (config.invocation_params.dir / arg.split("::", 1)[0]).exists()
        ]
        if missing and not config.option.pyargs:
            # xdist workers would report a missing path as "no tests ran"; fail as pytest does.
            raise pytest.UsageError(f"file or directory not found: {', '.join(missing)}")
        return worker_cap()
    workers = auto_worker_count(sum(file_weight(path) for path in files), worker_cap())
    if workers == 0:
        config.stash[_SIZED_SERIAL_KEY] = True
    return workers


def _spec_workers(spec: str) -> int:
    count, separator, _ = spec.partition("*")
    return int(count) if separator else 1


def distributed_workers(config: pytest.Config) -> int:
    """The worker processes xdist will start for this run (0 when the run is in-process).

    xdist turns ``-n``/``--maxprocesses`` into ``--tx`` specs before ``pytest_configure``, so
    the specs are the settled count. A negative setting, which xdist reads as no workers, is
    refused rather than run in-process without a serial reason.
    """

    for option, flag in (("numprocesses", "-n"), ("maxprocesses", "--maxprocesses")):
        value = config.getoption(option, default=None)
        if isinstance(value, int) and value < 0:
            raise pytest.UsageError(f"{flag} {value}: a worker count must not be negative.")
    if config.getoption("dist", default="no") == "no":
        return 0
    specs: list[str] = config.getoption("tx", default=None) or []
    return sum(_spec_workers(spec) for spec in specs)


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
    """Refuse a run above the worker cap, and a serial run that does not state why."""

    if hasattr(config, "workerinput"):  # xdist worker: the controller already checked
        return
    workers = distributed_workers(config)
    if workers > worker_cap():
        raise pytest.UsageError(
            f"This run asks for {workers} workers; backend tests run on at most "
            f"{worker_cap()} workers (MAX_WORKERS in tests/conftest.py). Drop -n to size "
            "the run to its selection, or ask for fewer workers."
        )
    if workers:
        return
    if config.stash.get(_SIZED_SERIAL_KEY, False):  # small selection: serial by design
        return
    reason = (config.getoption(SERIAL_REASON_OPTION) or "").strip()
    if not reason:
        raise pytest.UsageError(
            "This pytest run is serial (-n 0, --pdb, or addopts overridden). "
            "Backend tests run in parallel by default (a small selection runs "
            "in-process on its own); drop the serial flag, or state why "
            f'it must be serial with {SERIAL_REASON_OPTION} "<reason>" '
            '(for example: pdm run test-serial --serial-reason "pdb on <test>" <test>).'
        )
    config.stash[_SERIAL_REASON_KEY] = reason


def pytest_report_header(config: pytest.Config) -> str | None:
    reason = config.stash.get(_SERIAL_REASON_KEY, None)
    return f"serial run: {reason}" if reason else None
