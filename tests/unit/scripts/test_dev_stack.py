from __future__ import annotations

from collections.abc import Sequence

from scripts import dev_stack


class RecordingRunner:
    def __init__(self, exit_codes: Sequence[int] = ()) -> None:
        self.commands: list[tuple[str, ...]] = []
        self._exit_codes = list(exit_codes)

    def __call__(self, command: Sequence[str]) -> int:
        self.commands.append(tuple(command))
        if self._exit_codes:
            return self._exit_codes.pop(0)
        return 0


def test_start_runs_compose_up_then_db_upgrade() -> None:
    runner = RecordingRunner()

    result = dev_stack.main(["start"], runner=runner)

    assert result == 0
    assert runner.commands == [
        (*dev_stack.COMPOSE, "up", "-d"),
        dev_stack.DB_UPGRADE,
    ]


def test_build_start_clean_keeps_no_cache_build_as_explicit_subcommand() -> None:
    runner = RecordingRunner()

    result = dev_stack.main(["build-start-clean"], runner=runner)

    assert result == 0
    assert runner.commands == [
        (*dev_stack.COMPOSE, "build", "--no-cache"),
        (*dev_stack.COMPOSE, "up", "-d", "--force-recreate"),
        dev_stack.DB_UPGRADE,
    ]


def test_logs_can_target_specific_services() -> None:
    runner = RecordingRunner()

    result = dev_stack.main(["logs", "web"], runner=runner)

    assert result == 0
    assert runner.commands == [(*dev_stack.COMPOSE, "logs", "-f", "web")]


def test_runner_failure_stops_follow_on_commands() -> None:
    runner = RecordingRunner(exit_codes=[17])

    result = dev_stack.main(["start"], runner=runner)

    assert result == 17
    assert runner.commands == [(*dev_stack.COMPOSE, "up", "-d")]


def test_unknown_command_fails_without_running() -> None:
    runner = RecordingRunner()

    result = dev_stack.main(["wat"], runner=runner)

    assert result == 2
    assert runner.commands == []
