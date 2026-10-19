import pytest

from tests.fixtures.identity_fixtures import now

__all__ = ["now"]

SERIAL_REASON_OPTION = "--serial-reason"
_SERIAL_REASON_KEY = pytest.StashKey[str]()


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
    reason = (config.getoption(SERIAL_REASON_OPTION) or "").strip()
    if not reason:
        raise pytest.UsageError(
            "This pytest run is serial (-n 0, --pdb, or addopts overridden). "
            "Backend tests run in parallel by default; drop the serial flag, or state why "
            f'it must be serial with {SERIAL_REASON_OPTION} "<reason>" '
            '(for example: pdm run test-serial --serial-reason "pdb on <test>" <test>).'
        )
    config.stash[_SERIAL_REASON_KEY] = reason


def pytest_report_header(config: pytest.Config) -> str | None:
    reason = config.stash.get(_SERIAL_REASON_KEY, None)
    return f"serial run: {reason}" if reason else None
