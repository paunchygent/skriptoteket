"""Unit tests for the Skriptoteket Hemma staging lifecycle command.

Purpose:
    Pin the guarded argv sequence of `pdm run hemma-dev`: database before
    db-upgrade before web, import before fixture before the Vite unit, and a
    reset scoped to the skriptoteket-dev project.

Relationships:
    - Exercises `scripts/hemma_dev.py` with fake process and HTTP effects.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path

from scripts import hemma_dev

VITE_START = ("systemctl", "--user", "start", hemma_dev.VITE_UNIT)
VITE_ACTIVE = ("systemctl", "--user", "is-active", "--quiet", hemma_dev.VITE_UNIT)
VITE_STOP = ("systemctl", "--user", "stop", hemma_dev.VITE_UNIT)
START_SEQUENCE = [
    hemma_dev.NETWORK_CHECK,
    hemma_dev.DB_UP,
    hemma_dev.DB_UPGRADE,
    hemma_dev.APP_UP,
    hemma_dev.PROOF_IMPORT,
    hemma_dev.PROOF_FIXTURE,
    VITE_START,
    VITE_ACTIVE,
]


class FakeHost:
    def __init__(
        self,
        *,
        cwd: Path = hemma_dev.STAGING_CHECKOUT,
        environ: Mapping[str, str] | None = None,
        exit_codes: Mapping[tuple[str, ...], int] | None = None,
        ps_output: str = "",
        http: Mapping[str, int | None] | None = None,
        existing: set[Path] | None = None,
    ) -> None:
        self.commands: list[tuple[str, ...]] = []
        self.environments: list[Mapping[str, str]] = []
        self.installed: list[tuple[Path, Path]] = []
        self._exit_codes = dict(exit_codes or {})
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
        return self._exit_codes.get(tuple(command), 0)

    def _capture(self, command: Sequence[str], env: Mapping[str, str], cwd: Path) -> str:
        self.commands.append(tuple(command))
        return self._ps_output


def _healthy_ps() -> str:
    return "\n".join(
        json.dumps({"Service": service, "State": "running", "Health": "healthy"})
        for service in ("db", "web", "worker")
    )


def test_start_upgrades_database_before_web_and_imports_before_fixture_and_vite() -> None:
    fake = FakeHost()

    assert hemma_dev.main(["start"], host=fake.host) == 0

    assert fake.commands == START_SEQUENCE
    assert all(env["DOCKER_HOST"] == hemma_dev.ROOTLESS_DOCKER_HOST for env in fake.environments)
    assert hemma_dev.PROOF_IMPORT[-1] == "--apply"


def test_reset_removes_only_project_resources_then_runs_full_start() -> None:
    fake = FakeHost()

    assert hemma_dev.main(["reset"], host=fake.host) == 0

    assert fake.commands == [
        hemma_dev.NETWORK_CHECK,
        VITE_STOP,
        hemma_dev.RESET_STACK,
        *START_SEQUENCE,
    ]
    assert hemma_dev.RESET_STACK[:6] == hemma_dev.COMPOSE
    flattened = [token for command in fake.commands for token in command]
    assert "prune" not in flattened
    assert ("network", "rm") not in {tuple(c[1:3]) for c in fake.commands}


def test_failed_db_upgrade_stops_before_web_starts() -> None:
    fake = FakeHost(exit_codes={hemma_dev.DB_UPGRADE: 3})

    assert hemma_dev.main(["start"], host=fake.host) == 2

    assert fake.commands == [hemma_dev.NETWORK_CHECK, hemma_dev.DB_UP, hemma_dev.DB_UPGRADE]


def test_start_stops_when_huleedu_staging_inputs_are_missing() -> None:
    fake = FakeHost(existing={hemma_dev.IDENTITY_PUBLIC_KEY_HOST_PATH})

    assert hemma_dev.main(["start"], host=fake.host) == 2

    assert fake.commands == []


def test_start_stops_when_huleedu_network_is_missing() -> None:
    fake = FakeHost(exit_codes={hemma_dev.NETWORK_CHECK: 1})

    assert hemma_dev.main(["start"], host=fake.host) == 2

    assert fake.commands == [hemma_dev.NETWORK_CHECK]


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


def test_build_installs_frontend_dependencies_and_builds_web_and_runner() -> None:
    fake = FakeHost()

    assert hemma_dev.main(["build"], host=fake.host) == 0

    assert fake.commands == [hemma_dev.BUILD_FRONTEND_DEPENDENCIES, hemma_dev.BUILD_IMAGES]


def test_stop_stops_vite_then_containers_without_removing_volumes() -> None:
    fake = FakeHost()

    assert hemma_dev.main(["stop"], host=fake.host) == 0

    assert fake.commands == [VITE_STOP, hemma_dev.STOP_STACK]


def test_install_vite_unit_copies_versioned_unit_and_enables_it() -> None:
    fake = FakeHost()

    assert hemma_dev.main(["install-vite-unit"], host=fake.host) == 0

    assert fake.installed == [
        (
            hemma_dev.STAGING_CHECKOUT / "systemd" / hemma_dev.VITE_UNIT,
            hemma_dev.VITE_UNIT_DESTINATION,
        )
    ]
    assert fake.commands == [
        ("systemctl", "--user", "daemon-reload"),
        ("systemctl", "--user", "enable", hemma_dev.VITE_UNIT),
    ]


def test_status_is_healthy_when_services_web_and_frontend_are_healthy(capsys) -> None:
    fake = FakeHost(ps_output=_healthy_ps())

    assert hemma_dev.main(["status"], host=fake.host) == 0

    assert "skriptoteket-dev staging: healthy" in capsys.readouterr().out


def test_status_is_unhealthy_when_worker_or_frontend_is_down(capsys) -> None:
    ps_output = "\n".join(
        json.dumps({"Service": service, "State": "running", "Health": health})
        for service, health in (("db", "healthy"), ("web", "healthy"), ("worker", "unhealthy"))
    )
    fake = FakeHost(
        ps_output=ps_output, http={hemma_dev.WEB_HEALTH_URL: 200, hemma_dev.VITE_URL: None}
    )

    assert hemma_dev.main(["status"], host=fake.host) == 1

    output = capsys.readouterr().out
    assert "worker: unhealthy" in output
    assert "skriptoteket-dev staging: unhealthy" in output


def test_service_health_accepts_json_array_output() -> None:
    output = json.dumps([{"Service": "db", "State": "running", "Health": "healthy"}])

    assert hemma_dev.service_health(output) == {"db": "healthy"}
