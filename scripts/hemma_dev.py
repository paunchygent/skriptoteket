"""Operate Skriptoteket staging on Hemma beside HuleEdu staging.

`pdm run hemma-dev <build|start|status|stop|reset|install-vite-unit>` runs only
from the Hemma staging checkout and drives the rootless Docker daemon, the
`compose.hemma-dev.yaml` project `skriptoteket-dev`, and the Skriptoteket Vite
user unit. Start and reset bring up the database, apply `db-upgrade`, start
web and worker, import the HuleEdu staging proof subjects with `--apply`, ensure
the staging proof fixture, and then start the Vite unit.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.error import URLError
from urllib.request import urlopen

STAGING_CHECKOUT = Path("/home/paunchygent/apps/skriptoteket-dev")
PRODUCTION_CHECKOUT = Path("/home/paunchygent/apps/skriptoteket")
ROOTLESS_DOCKER_HOST = "unix:///run/user/1000/docker.sock"
COMPOSE_PROJECT = "skriptoteket-dev"
COMPOSE_FILE = "compose.hemma-dev.yaml"
COMPOSE: tuple[str, ...] = ("docker", "compose", "-f", COMPOSE_FILE, "-p", COMPOSE_PROJECT)
HULEEDU_NETWORK = "huleedu-dev_hule-network"
HEALTHY_SERVICES: tuple[str, ...] = ("db", "web", "worker")
WAIT_TIMEOUT_SECONDS = "300"

PROOF_EXPORT_HOST_PATH = Path(
    "/home/paunchygent/apps/huleedu-dev/output/skriptoteket-proof-identities/subject-export.json"
)
PROOF_EXPORT_CONTAINER_PATH = "/run/huleedu/proof-identities/subject-export.json"
IDENTITY_PUBLIC_KEY_HOST_PATH = Path(
    "/home/paunchygent/apps/huleedu-dev/secrets/local-runtime/internal-identity/"
    "gateway-internal-identity-public-key.pem"
)

VITE_UNIT = "skriptoteket-vite-dev.service"
VITE_UNIT_SOURCE = Path("systemd") / VITE_UNIT
VITE_UNIT_DESTINATION = Path.home() / ".config" / "systemd" / "user" / VITE_UNIT
WEB_HEALTH_URL = "http://127.0.0.1:18000/healthz"
VITE_URL = "http://127.0.0.1:5173"

COMPOSE_OVERRIDE_VARIABLES = (
    "COMPOSE_FILE",
    "COMPOSE_PROJECT_NAME",
    "COMPOSE_PROFILES",
    "DOCKER_CONTEXT",
)

DB_UP: tuple[str, ...] = (
    *COMPOSE,
    "up",
    "-d",
    "--no-build",
    "--wait",
    "--wait-timeout",
    WAIT_TIMEOUT_SECONDS,
    "db",
)
DB_UPGRADE: tuple[str, ...] = (
    *COMPOSE,
    "run",
    "--rm",
    "--no-deps",
    "web",
    "pdm",
    "run",
    "db-upgrade",
)
APP_UP: tuple[str, ...] = (
    *COMPOSE,
    "up",
    "-d",
    "--no-build",
    "--wait",
    "--wait-timeout",
    WAIT_TIMEOUT_SECONDS,
    "web",
    "worker",
)
PROOF_IMPORT: tuple[str, ...] = (
    *COMPOSE,
    "run",
    "--rm",
    "--no-deps",
    "web",
    "pdm",
    "run",
    "consume-huleedu-subject-export",
    "--export-json",
    PROOF_EXPORT_CONTAINER_PATH,
    "--apply",
)
PROOF_FIXTURE: tuple[str, ...] = (
    *COMPOSE,
    "run",
    "--rm",
    "--no-deps",
    "web",
    "pdm",
    "run",
    "setup-staging-proof-fixture",
    "--export-json",
    PROOF_EXPORT_CONTAINER_PATH,
)
PNPM = "/home/paunchygent/.local/bin/pnpm"
BUILD_FRONTEND_DEPENDENCIES: tuple[str, ...] = (PNPM, "install", "--frozen-lockfile")
BUILD_IMAGES: tuple[str, ...] = (*COMPOSE, "--profile", "build-only", "build", "web", "runner")
STOP_STACK: tuple[str, ...] = (*COMPOSE, "stop")
RESET_STACK: tuple[str, ...] = (*COMPOSE, "down", "--volumes", "--remove-orphans")
NETWORK_CHECK: tuple[str, ...] = (
    "docker",
    "network",
    "inspect",
    "--format",
    "{{.Name}}",
    HULEEDU_NETWORK,
)
COMPOSE_PS_JSON: tuple[str, ...] = (*COMPOSE, "ps", "--all", "--format", "json")


class HemmaDevError(RuntimeError):
    """Raised when the staging lifecycle fails closed."""


def _run_subprocess(command: Sequence[str], env: Mapping[str, str], cwd: Path) -> int:
    return subprocess.run(list(command), env=dict(env), cwd=cwd, check=False).returncode


def _capture_subprocess(command: Sequence[str], env: Mapping[str, str], cwd: Path) -> str:
    completed = subprocess.run(
        list(command), env=dict(env), cwd=cwd, check=False, capture_output=True, text=True
    )
    if completed.returncode != 0:
        return ""
    return completed.stdout


def _http_status(url: str) -> int | None:
    try:
        with urlopen(url, timeout=3.0) as response:  # noqa: S310 - fixed loopback URLs
            return int(response.status)
    except URLError as exc:
        status = getattr(exc, "code", None)
        return int(status) if isinstance(status, int) else None
    except OSError:
        return None


def _install_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)


@dataclass
class Host:
    """Process, HTTP, and filesystem effects; tests substitute fakes."""

    cwd: Path
    environ: Mapping[str, str]
    run: Callable[[Sequence[str], Mapping[str, str], Path], int] = _run_subprocess
    capture: Callable[[Sequence[str], Mapping[str, str], Path], str] = _capture_subprocess
    http_status: Callable[[str], int | None] = _http_status
    sleep: Callable[[float], None] = time.sleep
    path_exists: Callable[[Path], bool] = Path.is_file
    install_file: Callable[[Path, Path], None] = _install_file


class Lifecycle:
    """Guarded staging lifecycle actions."""

    def __init__(self, host: Host) -> None:
        self._host = host
        self._env = staging_environment(host.environ)

    def _run(self, command: Sequence[str], *, cwd: Path | None = None) -> None:
        code = self._host.run(command, self._env, cwd or STAGING_CHECKOUT)
        if code != 0:
            raise HemmaDevError(f"Command failed with exit {code}: {' '.join(command)}")

    def _wait_for(self, url: str, *, accept: Callable[[int], bool], timeout: float = 120.0) -> None:
        deadline = time.monotonic() + timeout
        while True:
            status = self._host.http_status(url)
            if status is not None and accept(status):
                return
            if time.monotonic() >= deadline:
                raise HemmaDevError(f"Staging endpoint did not become ready: {url}")
            self._host.sleep(1.0)

    def preflight(self) -> None:
        for required in (PROOF_EXPORT_HOST_PATH, IDENTITY_PUBLIC_KEY_HOST_PATH):
            if not self._host.path_exists(required):
                raise HemmaDevError(f"Required HuleEdu staging input is missing: {required}")
        if self._host.run(NETWORK_CHECK, self._env, STAGING_CHECKOUT) != 0:
            raise HemmaDevError(f"HuleEdu staging network is missing: {HULEEDU_NETWORK}")

    def build(self) -> None:
        self._run(BUILD_FRONTEND_DEPENDENCIES, cwd=STAGING_CHECKOUT / "frontend")
        self._run(BUILD_IMAGES)

    def start(self) -> None:
        self.preflight()
        self._run(DB_UP)
        self._run(DB_UPGRADE)
        self._run(APP_UP)
        self._wait_for(WEB_HEALTH_URL, accept=lambda status: status == 200)
        self._run(PROOF_IMPORT)
        self._run(PROOF_FIXTURE)
        self._run(("systemctl", "--user", "start", VITE_UNIT))
        self._run(("systemctl", "--user", "is-active", "--quiet", VITE_UNIT))
        self._wait_for(VITE_URL, accept=lambda status: status < 500)

    def stop(self) -> None:
        self._run(("systemctl", "--user", "stop", VITE_UNIT))
        self._run(STOP_STACK)

    def reset(self) -> None:
        self.preflight()
        self._run(("systemctl", "--user", "stop", VITE_UNIT))
        self._run(RESET_STACK)
        self.start()

    def install_vite_unit(self) -> None:
        self._host.install_file(STAGING_CHECKOUT / VITE_UNIT_SOURCE, VITE_UNIT_DESTINATION)
        self._run(("systemctl", "--user", "daemon-reload"))
        self._run(("systemctl", "--user", "enable", VITE_UNIT))

    def status(self) -> int:
        """Report web, worker, database, and frontend health; non-zero when unhealthy."""
        healthy = True
        health = service_health(self._host.capture(COMPOSE_PS_JSON, self._env, STAGING_CHECKOUT))
        for service in HEALTHY_SERVICES:
            state = health.get(service, "missing")
            healthy &= state == "healthy"
            print(f"{service}: {state}")

        web_status = self._host.http_status(WEB_HEALTH_URL)
        healthy &= web_status == 200
        print(
            f"web /healthz ({WEB_HEALTH_URL}): {web_status if web_status is not None else 'unreachable'}"
        )

        unit_active = (
            self._host.run(
                ("systemctl", "--user", "is-active", "--quiet", VITE_UNIT),
                self._env,
                STAGING_CHECKOUT,
            )
            == 0
        )
        vite_status = self._host.http_status(VITE_URL)
        frontend_ok = unit_active and vite_status is not None and vite_status < 500
        healthy &= frontend_ok
        print(
            f"frontend ({VITE_UNIT}, {VITE_URL}): "
            f"{'healthy' if frontend_ok else 'unhealthy'} "
            f"(unit {'active' if unit_active else 'inactive'}, "
            f"http {vite_status if vite_status is not None else 'unreachable'})"
        )
        print(f"skriptoteket-dev staging: {'healthy' if healthy else 'unhealthy'}")
        return 0 if healthy else 1


def staging_environment(base: Mapping[str, str]) -> dict[str, str]:
    """Return the environment that pins every Docker call to the rootless daemon."""
    environment = {
        key: value for key, value in base.items() if key not in COMPOSE_OVERRIDE_VARIABLES
    }
    environment["DOCKER_HOST"] = ROOTLESS_DOCKER_HOST
    return environment


def validate_invocation(*, cwd: Path, environ: Mapping[str, str]) -> None:
    """Refuse every invocation outside the Hemma staging checkout."""
    resolved = cwd.resolve()
    if resolved == PRODUCTION_CHECKOUT.resolve():
        raise HemmaDevError("Refusing the production Skriptoteket checkout.")
    if resolved != STAGING_CHECKOUT.resolve():
        raise HemmaDevError(
            f"Run from the Hemma staging checkout {STAGING_CHECKOUT}, not {resolved}."
        )
    docker_host = environ.get("DOCKER_HOST", "")
    if docker_host not in ("", ROOTLESS_DOCKER_HOST):
        raise HemmaDevError(
            f"DOCKER_HOST must be unset or {ROOTLESS_DOCKER_HOST}, got {docker_host}."
        )
    for variable in COMPOSE_OVERRIDE_VARIABLES:
        if environ.get(variable, ""):
            raise HemmaDevError(f"{variable} must be unset for the Hemma staging lane.")


def service_health(compose_ps_output: str) -> dict[str, str]:
    """Map Compose service names to their health (or state when no healthcheck)."""
    text = compose_ps_output.strip()
    if not text:
        return {}
    if text.startswith("["):
        rows = json.loads(text)
    else:
        rows = [json.loads(line) for line in text.splitlines() if line.strip()]
    return {
        str(row.get("Service")): str(row.get("Health") or row.get("State") or "unknown")
        for row in rows
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pdm run hemma-dev",
        description="Operate Skriptoteket staging (skriptoteket-dev) on Hemma.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name, summary in (
        ("build", "Install frontend dependencies and build web and runner images."),
        ("start", "Start db, db-upgrade, web and worker, import proof subjects, fixture, Vite."),
        ("status", "Report web, worker, database, and frontend health."),
        ("stop", "Stop the Vite unit and the skriptoteket-dev containers."),
        ("reset", "Remove skriptoteket-dev containers and volumes, then start."),
        ("install-vite-unit", "Install and enable the Skriptoteket Vite user unit."),
    ):
        subparsers.add_parser(name, help=summary)
    return parser


def main(argv: Sequence[str] | None = None, *, host: Host | None = None) -> int:
    args = build_parser().parse_args(sys.argv[1:] if argv is None else argv)
    active_host = host or Host(cwd=Path.cwd(), environ=os.environ)
    try:
        validate_invocation(cwd=active_host.cwd, environ=active_host.environ)
        lifecycle = Lifecycle(active_host)
        if args.command == "status":
            return lifecycle.status()
        {
            "build": lifecycle.build,
            "start": lifecycle.start,
            "stop": lifecycle.stop,
            "reset": lifecycle.reset,
            "install-vite-unit": lifecycle.install_vite_unit,
        }[args.command]()
    except HemmaDevError as exc:
        print(f"hemma-dev: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
