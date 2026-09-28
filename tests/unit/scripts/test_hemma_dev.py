"""Unit tests for the Skriptoteket Hemma staging lifecycle command.

Purpose:
    Prove the outcomes of `pdm run hemma-dev`: it refuses every target except
    the Hemma staging checkout on the rootless daemon, stops before touching
    containers when HuleEdu staging inputs are missing, upgrades the database
    before web starts, applies the proof import before the fixture and the Vite
    unit, stops on the first failure, keeps volumes on stop, and resets only
    this project's own resources.

Relationships:
    - Exercises `scripts/hemma_dev.py` with fake process and HTTP effects.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

import pytest

from scripts import hemma_dev

ROOT = Path(__file__).resolve().parents[3]

Command = tuple[str, ...]


def is_db_up(command: Command) -> bool:
    return "up" in command and command[-1] == "db"


def is_db_upgrade(command: Command) -> bool:
    return "db-upgrade" in command


def is_app_up(command: Command) -> bool:
    return "up" in command and "web" in command


def is_proof_import(command: Command) -> bool:
    return "consume-huleedu-subject-export" in command


def is_fixture(command: Command) -> bool:
    return "setup-staging-proof-fixture" in command


def is_vite_start(command: Command) -> bool:
    return command[:3] == ("systemctl", "--user", "start") and hemma_dev.VITE_UNIT in command


def is_vite_stop(command: Command) -> bool:
    return command[:3] == ("systemctl", "--user", "stop") and hemma_dev.VITE_UNIT in command


def is_volume_removal(command: Command) -> bool:
    return "down" in command and "--volumes" in command


def is_compose(command: Command) -> bool:
    return command[:2] == ("docker", "compose")


class FakeHost:
    def __init__(
        self,
        *,
        cwd: Path = hemma_dev.STAGING_CHECKOUT,
        environ: Mapping[str, str] | None = None,
        fail: Callable[[Command], bool] = lambda _command: False,
        ps_output: str = "",
        http: Mapping[str, int | None] | None = None,
        existing: set[Path] | None = None,
    ) -> None:
        self.commands: list[Command] = []
        self.environments: list[Mapping[str, str]] = []
        self.installed: list[tuple[Path, Path]] = []
        self._fail = fail
        self._ps_output = ps_output
        self._http = dict(http or {hemma_dev.WEB_HEALTH_URL: 200, hemma_dev.VITE_URL: 200})
        self._existing = (
            existing
            if existing is not None
            else {hemma_dev.PROOF_EXPORT_HOST_PATH, hemma_dev.IDENTITY_PUBLIC_KEY_HOST_PATH}
        )
        self.host = hemma_dev.Host(
            cwd=cwd,
            environ=environ if environ is not None else {"PATH": "/usr/bin"},
            run=self._run,
            capture=self._capture,
            http_status=self._http.get,
            sleep=lambda _seconds: None,
            path_exists=lambda path: path in self._existing,
            install_file=lambda source, destination: self.installed.append((source, destination)),
        )

    def _run(self, command: Sequence[str], env: Mapping[str, str], cwd: Path) -> int:
        self.commands.append(tuple(command))
        self.environments.append(env)
        return 1 if self._fail(tuple(command)) else 0

    def _capture(self, command: Sequence[str], env: Mapping[str, str], cwd: Path) -> str:
        self.commands.append(tuple(command))
        return self._ps_output

    def index(self, matches: Callable[[Command], bool]) -> int:
        (position,) = [i for i, command in enumerate(self.commands) if matches(command)]
        return position

    def ran(self, matches: Callable[[Command], bool]) -> bool:
        return any(matches(command) for command in self.commands)


def test_start_upgrades_database_before_web_and_applies_import_before_fixture_and_vite() -> None:
    fake = FakeHost()

    assert hemma_dev.main(["start"], host=fake.host) == 0

    order = [
        fake.index(step)
        for step in (is_db_up, is_db_upgrade, is_app_up, is_proof_import, is_fixture, is_vite_start)
    ]
    assert order == sorted(order)
    assert "--apply" in fake.commands[fake.index(is_proof_import)]
    assert all(env["DOCKER_HOST"] == hemma_dev.ROOTLESS_DOCKER_HOST for env in fake.environments)


def test_failed_db_upgrade_stops_before_web_starts() -> None:
    fake = FakeHost(fail=is_db_upgrade)

    assert hemma_dev.main(["start"], host=fake.host) == 2

    assert not fake.ran(is_app_up)
    assert not fake.ran(is_proof_import)
    assert not fake.ran(is_vite_start)


def test_failed_fixture_stops_before_the_frontend_starts() -> None:
    fake = FakeHost(fail=is_fixture)

    assert hemma_dev.main(["start"], host=fake.host) == 2

    assert not fake.ran(is_vite_start)


@pytest.mark.parametrize("action", ["start", "reset", "fixture"])
def test_missing_huleedu_staging_inputs_stop_before_any_command(action: str) -> None:
    fake = FakeHost(existing={hemma_dev.IDENTITY_PUBLIC_KEY_HOST_PATH})

    assert hemma_dev.main([action], host=fake.host) == 2

    assert fake.commands == []


@pytest.mark.parametrize("action", ["start", "reset", "fixture"])
def test_missing_huleedu_network_stops_before_any_compose_command(action: str) -> None:
    fake = FakeHost(fail=lambda command: hemma_dev.HULEEDU_NETWORK in command)

    assert hemma_dev.main([action], host=fake.host) == 2

    assert not fake.ran(is_compose)
    assert not fake.ran(is_vite_stop)


def test_reset_removes_only_project_volumes_then_runs_a_full_start() -> None:
    fake = FakeHost()

    assert hemma_dev.main(["reset"], host=fake.host) == 0

    removal = fake.commands[fake.index(is_volume_removal)]
    assert removal[: len(hemma_dev.COMPOSE)] == hemma_dev.COMPOSE
    assert fake.index(is_vite_stop) < fake.index(is_volume_removal) < fake.index(is_db_up)
    assert fake.index(is_fixture) < fake.index(is_vite_start)
    assert not any("prune" in command for command in fake.commands)
    assert not any(command[1:3] == ("network", "rm") for command in fake.commands)


def test_fixture_reruns_only_the_fixture() -> None:
    fake = FakeHost()

    assert hemma_dev.main(["fixture"], host=fake.host) == 0

    assert [command for command in fake.commands if is_compose(command)] == [
        fake.commands[fake.index(is_fixture)]
    ]


def test_stop_stops_the_frontend_and_keeps_volumes() -> None:
    fake = FakeHost()

    assert hemma_dev.main(["stop"], host=fake.host) == 0

    assert fake.ran(is_vite_stop)
    assert not fake.ran(is_volume_removal)


def test_failed_frontend_dependency_install_stops_the_build() -> None:
    fake = FakeHost(fail=lambda _command: True)

    assert hemma_dev.main(["build"], host=fake.host) == 2

    assert len(fake.commands) == 1


def test_refuses_production_and_other_checkouts() -> None:
    for cwd in (hemma_dev.PRODUCTION_CHECKOUT, Path("/tmp")):
        fake = FakeHost(cwd=cwd)
        assert hemma_dev.main(["start"], host=fake.host) == 2
        assert fake.commands == []


def test_refuses_compose_and_docker_overrides() -> None:
    for environ in (
        {"DOCKER_HOST": "unix:///var/run/docker.sock"},
        {"COMPOSE_PROJECT_NAME": "skriptoteket"},
        {"DOCKER_CONTEXT": "default"},
    ):
        fake = FakeHost(environ=environ)
        assert hemma_dev.main(["status"], host=fake.host) == 2
        assert fake.commands == []


def test_install_vite_unit_installs_the_versioned_unit_and_enables_it() -> None:
    fake = FakeHost()

    assert hemma_dev.main(["install-vite-unit"], host=fake.host) == 0

    ((source, destination),) = fake.installed
    assert (ROOT / source.relative_to(hemma_dev.STAGING_CHECKOUT)).is_file()
    assert destination.name == hemma_dev.VITE_UNIT
    assert destination.parent == Path.home() / ".config" / "systemd" / "user"
    assert fake.ran(lambda command: "enable" in command and hemma_dev.VITE_UNIT in command)


def _ps(health: Mapping[str, str]) -> str:
    return "\n".join(
        json.dumps({"Service": service, "State": "running", "Health": state})
        for service, state in health.items()
    )


def test_status_is_healthy_when_services_web_and_frontend_are_healthy(capsys) -> None:
    fake = FakeHost(ps_output=_ps({"db": "healthy", "web": "healthy", "worker": "healthy"}))

    assert hemma_dev.main(["status"], host=fake.host) == 0

    assert "skriptoteket-dev staging: healthy" in capsys.readouterr().out


def test_status_is_unhealthy_when_worker_or_frontend_is_down(capsys) -> None:
    fake = FakeHost(
        ps_output=_ps({"db": "healthy", "web": "healthy", "worker": "unhealthy"}),
        http={hemma_dev.WEB_HEALTH_URL: 200, hemma_dev.VITE_URL: None},
    )

    assert hemma_dev.main(["status"], host=fake.host) == 1

    output = capsys.readouterr().out
    assert "worker: unhealthy" in output
    assert "skriptoteket-dev staging: unhealthy" in output


def test_status_is_unhealthy_when_a_service_is_missing(capsys) -> None:
    fake = FakeHost(ps_output=_ps({"db": "healthy", "web": "healthy"}))

    assert hemma_dev.main(["status"], host=fake.host) == 1

    assert "worker: missing" in capsys.readouterr().out


def test_service_health_accepts_json_array_output() -> None:
    output = json.dumps([{"Service": "db", "State": "running", "Health": "healthy"}])

    assert hemma_dev.service_health(output) == {"db": "healthy"}
