from __future__ import annotations

from collections.abc import Sequence

from scripts import obs_stack


class RecordingRunner:
    def __init__(self) -> None:
        self.commands: list[tuple[str, ...]] = []

    def __call__(self, command: Sequence[str]) -> int:
        self.commands.append(tuple(command))
        return 0


def test_start_runs_observability_compose_up() -> None:
    runner = RecordingRunner()

    result = obs_stack.main(["start"], runner=runner)

    assert result == 0
    assert runner.commands == [(*obs_stack.COMPOSE, "up", "-d")]


def test_logs_can_target_specific_services() -> None:
    runner = RecordingRunner()

    result = obs_stack.main(["logs", "grafana"], runner=runner)

    assert result == 0
    assert runner.commands == [(*obs_stack.COMPOSE, "logs", "-f", "grafana")]
