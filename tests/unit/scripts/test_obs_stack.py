from __future__ import annotations

from collections.abc import Sequence

import pytest

from scripts import obs_stack


class RecordingRunner:
    def __init__(self) -> None:
        self.commands: list[tuple[str, ...]] = []

    def __call__(self, command: Sequence[str]) -> int:
        self.commands.append(tuple(command))
        return 0


def test_start_runs_observability_compose_up_through_agent_secrets() -> None:
    runner = RecordingRunner()

    result = obs_stack.main(["start"], runner=runner)

    assert result == 0
    assert runner.commands == [(*obs_stack.COMPOSE_WITH_SECRETS, "up", "-d")]
    command = runner.commands[0]
    assert command[:5] == ("agent-secrets", "run", "--set", "skriptoteket-prod", "--")
    assert command[-2:] == ("up", "-d")
    assert "compose.secrets.observability.yaml" in command


@pytest.mark.parametrize("action", ["stop", "restart", "logs", "status"])
def test_non_creating_commands_use_the_base_compose_file_only(action: str) -> None:
    runner = RecordingRunner()

    result = obs_stack.main([action], runner=runner)

    assert result == 0
    (command,) = runner.commands
    assert command[: len(obs_stack.COMPOSE)] == obs_stack.COMPOSE
    assert command[0] != "agent-secrets"
    assert "compose.secrets.observability.yaml" not in command


def test_logs_can_target_specific_services() -> None:
    runner = RecordingRunner()

    result = obs_stack.main(["logs", "grafana"], runner=runner)

    assert result == 0
    assert runner.commands == [(*obs_stack.COMPOSE, "logs", "-f", "grafana")]
