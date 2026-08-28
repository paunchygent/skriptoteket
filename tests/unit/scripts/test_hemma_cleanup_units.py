import configparser
import os
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
WRAPPER = REPOSITORY_ROOT / "scripts" / "hemma_cleanup_if_running.sh"
INSTALLER = REPOSITORY_ROOT / "scripts" / "install_hemma_cleanup_units.sh"
SELECTORS = ("cleanup-session-files", "cleanup-sandbox-snapshots")
TIMER_NAMES = (
    "skriptoteket-session-files-cleanup.timer",
    "skriptoteket-sandbox-snapshots-cleanup.timer",
)
UNIT_NAMES = tuple(timer.removesuffix(".timer") for timer in TIMER_NAMES)
INSTALLER_MODE_STRINGS = ["0755", "0644", "0644", "0644", "0644"]
INSTALLED_FILE_MODES = [0o755, 0o644, 0o644, 0o644, 0o644]


def _run_bash(
    script: str, *arguments: str, environment: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "-s", "--", *arguments],
        check=False,
        cwd=REPOSITORY_ROOT,
        env={**os.environ, **environment},
        input=script,
        text=True,
        capture_output=True,
    )


def _write_fake_docker(tmp_path: Path) -> tuple[Path, Path]:
    command_log = tmp_path / "docker-argv.bin"
    docker = tmp_path / "docker"
    docker.write_text(
        """#!/usr/bin/env bash
set -u
printf '%s\\0' "$@" >> "$FAKE_DOCKER_LOG"
printf '\\0' >> "$FAKE_DOCKER_LOG"
case "$1" in
  ps)
    printf '%s' "$FAKE_PS_STDOUT"
    printf '%s' "$FAKE_PS_STDERR" >&2
    exit "$FAKE_PS_STATUS"
    ;;
  inspect)
    printf '%s' "$FAKE_INSPECT_STDOUT"
    printf '%s' "$FAKE_INSPECT_STDERR" >&2
    exit "$FAKE_INSPECT_STATUS"
    ;;
  exec)
    printf '%s' "$FAKE_EXEC_STDOUT"
    printf '%s' "$FAKE_EXEC_STDERR" >&2
    exit "$FAKE_EXEC_STATUS"
    ;;
esac
exit 90
""",
        encoding="utf-8",
    )
    docker.chmod(0o755)
    return docker, command_log


def _docker_calls(command_log: Path) -> list[list[str]]:
    values = command_log.read_bytes().split(b"\0")
    calls: list[list[str]] = []
    current: list[str] = []
    for value in values:
        if value:
            current.append(value.decode("utf-8"))
        elif current:
            calls.append(current)
            current = []
    return calls


def _run_wrapper(
    tmp_path: Path,
    selector: str,
    *,
    ps_stdout: str = "",
    ps_status: int = 0,
    ps_stderr: str = "",
    inspect_stdout: str = "false",
    inspect_status: int = 0,
    inspect_stderr: str = "",
    exec_status: int = 0,
    exec_stdout: str = "",
    exec_stderr: str = "",
) -> tuple[subprocess.CompletedProcess[str], list[list[str]]]:
    docker, command_log = _write_fake_docker(tmp_path)
    result = _run_bash(
        'source "$1"\ndocker_command=("$2")\nmain "$3"\n',
        str(WRAPPER),
        str(docker),
        selector,
        environment={
            "FAKE_DOCKER_LOG": str(command_log),
            "FAKE_PS_STDOUT": ps_stdout,
            "FAKE_PS_STDERR": ps_stderr,
            "FAKE_PS_STATUS": str(ps_status),
            "FAKE_INSPECT_STDOUT": inspect_stdout,
            "FAKE_INSPECT_STDERR": inspect_stderr,
            "FAKE_INSPECT_STATUS": str(inspect_status),
            "FAKE_EXEC_STDOUT": exec_stdout,
            "FAKE_EXEC_STDERR": exec_stderr,
            "FAKE_EXEC_STATUS": str(exec_status),
        },
    )
    return result, _docker_calls(command_log)


@pytest.mark.parametrize("selector", SELECTORS)
def test_wrapper_absent_skips_inspection_and_cleanup(tmp_path: Path, selector: str) -> None:
    result, calls = _run_wrapper(tmp_path, selector)

    assert result.returncode == 0
    assert "state=absent" in result.stdout
    assert calls == [
        ["ps", "--all", "--filter", "name=^/skriptoteket-web$", "--format", "{{.Names}}"]
    ]


@pytest.mark.parametrize("selector", SELECTORS)
def test_wrapper_skips_proven_stopped_without_cleanup(tmp_path: Path, selector: str) -> None:
    result, calls = _run_wrapper(tmp_path, selector, ps_stdout="skriptoteket-web")

    assert result.returncode == 0
    assert "state=stopped" in result.stdout
    assert [call[0] for call in calls] == ["ps", "inspect"]


@pytest.mark.parametrize("selector", SELECTORS)
def test_wrapper_running_preserves_cleanup_result(tmp_path: Path, selector: str) -> None:
    result, calls = _run_wrapper(
        tmp_path,
        selector,
        ps_stdout="skriptoteket-web",
        inspect_stdout="true",
        exec_status=37,
        exec_stdout="cleanup output\n",
        exec_stderr="cleanup command failed\n",
    )

    assert result.returncode == 37
    assert "cleanup output" in result.stdout
    assert "cleanup command failed" in result.stderr
    assert calls[-1] == [
        "exec",
        "-e",
        "PYTHONPATH=/app/src",
        "skriptoteket-web",
        "pdm",
        "run",
        "python",
        "-m",
        "skriptoteket.cli",
        selector,
    ]


@pytest.mark.parametrize("selector", SELECTORS)
@pytest.mark.parametrize(
    ("ps_status", "ps_stderr", "inspect_status", "inspect_stderr", "expected_status", "diagnostic"),
    [
        (41, "Docker ps denied\n", 0, "", 41, "Docker ps denied"),
        (0, "", 42, "Docker inspect denied\n", 42, "Docker inspect denied"),
    ],
)
def test_wrapper_preserves_docker_failures(
    tmp_path: Path,
    selector: str,
    ps_status: int,
    ps_stderr: str,
    inspect_status: int,
    inspect_stderr: str,
    expected_status: int,
    diagnostic: str,
) -> None:
    result, calls = _run_wrapper(
        tmp_path,
        selector,
        ps_stdout="skriptoteket-web" if ps_status == 0 else "",
        ps_status=ps_status,
        ps_stderr=ps_stderr,
        inspect_status=inspect_status,
        inspect_stderr=inspect_stderr,
    )

    assert result.returncode == expected_status
    assert diagnostic in result.stderr
    assert "exec" not in [call[0] for call in calls]


@pytest.mark.parametrize(
    ("ps_stdout", "inspect_stdout", "expected_diagnostic", "expected_calls"),
    [
        ("skriptoteket-web\nother", "false", "Expected exactly one container", ["ps"]),
        ("skriptoteket-web ", "false", "Expected exactly one container", ["ps"]),
        ("skriptoteket-web", "maybe", "Expected Docker running state", ["ps", "inspect"]),
    ],
)
def test_wrapper_rejects_ambiguous_container_or_malformed_running_state(
    tmp_path: Path,
    ps_stdout: str,
    inspect_stdout: str,
    expected_diagnostic: str,
    expected_calls: list[str],
) -> None:
    result, calls = _run_wrapper(
        tmp_path,
        "cleanup-session-files",
        ps_stdout=ps_stdout,
        inspect_stdout=inspect_stdout,
    )

    assert result.returncode == 1
    assert expected_diagnostic in result.stderr
    assert [call[0] for call in calls] == expected_calls


def test_wrapper_invalid_selector_does_not_cleanup(tmp_path: Path) -> None:
    result, calls = _run_wrapper(
        tmp_path,
        "cleanup-login-events",
        ps_stdout="skriptoteket-web",
        inspect_stdout="true",
    )

    assert result.returncode == 2
    assert "Unsupported cleanup selector" in result.stderr
    assert [call[0] for call in calls] == ["ps", "inspect"]
    idle_path = tmp_path / "idle"
    idle_path.mkdir()
    idle_result, _ = _run_wrapper(idle_path, "cleanup-login-events")
    assert idle_result.returncode == 2


def _unit(path: Path) -> configparser.ConfigParser:
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(path, encoding="utf-8")
    return parser


def _installer_values(lines: list[str], prefix: str) -> list[str]:
    return [line.removeprefix(prefix) for line in lines if line.startswith(prefix)]


@pytest.mark.parametrize(
    ("name", "description", "timer_description", "selector"),
    [
        (
            "skriptoteket-session-files-cleanup",
            "Skriptoteket: cleanup expired session files",
            "Run Skriptoteket session file cleanup hourly",
            "cleanup-session-files",
        ),
        (
            "skriptoteket-sandbox-snapshots-cleanup",
            "Skriptoteket sandbox snapshot cleanup",
            "Run sandbox snapshot cleanup hourly",
            "cleanup-sandbox-snapshots",
        ),
    ],
)
def test_unit_sources_define_the_two_hourly_wrapper_timers(
    name: str,
    description: str,
    timer_description: str,
    selector: str,
) -> None:
    service = _unit(REPOSITORY_ROOT / "systemd" / f"{name}.service")
    timer = _unit(REPOSITORY_ROOT / "systemd" / f"{name}.timer")

    assert service["Unit"]["description"] == description
    assert service["Unit"]["requires"] == "snap.docker.dockerd.service"
    assert service["Unit"]["after"] == "snap.docker.dockerd.service"
    assert service["Service"]["type"] == "oneshot"
    assert (
        service["Service"]["execstart"]
        == f"/usr/local/libexec/skriptoteket-cleanup-if-running {selector}"
    )
    assert "workingdirectory" not in service["Service"]
    assert timer["Unit"]["description"] == timer_description
    assert timer["Timer"]["oncalendar"] == "hourly"
    assert timer["Timer"]["persistent"] == "true"
    assert timer["Install"]["wantedby"] == "timers.target"


def test_installer_declares_only_the_five_accepted_production_destinations() -> None:
    result = _run_bash(
        """source "$1"
for item in "${sources[@]}"; do printf 'source=%s\\n' "$item"; done
for item in "${destinations[@]}"; do printf 'destination=%s\\n' "$item"; done
for item in "${modes[@]}"; do printf 'mode=%s\\n' "$item"; done
for item in "${timers[@]}"; do printf 'timer=%s\\n' "$item"; done
printf 'libexec=%s\\n' "$libexec_dir"
printf 'systemctl=%s\\n' "${systemctl_command[*]}"
""",
        str(INSTALLER),
        environment={},
    )

    assert result.returncode == 0
    lines = result.stdout.splitlines()
    assert _installer_values(lines, "source=") == [
        str(WRAPPER),
        *(
            str(REPOSITORY_ROOT / "systemd" / f"{name}.{kind}")
            for name in UNIT_NAMES
            for kind in ("service", "timer")
        ),
    ]
    assert _installer_values(lines, "destination=") == [
        "/usr/local/libexec/skriptoteket-cleanup-if-running",
        *(
            f"/etc/systemd/system/{name}.{kind}"
            for name in UNIT_NAMES
            for kind in ("service", "timer")
        ),
    ]
    assert _installer_values(lines, "mode=") == INSTALLER_MODE_STRINGS
    assert _installer_values(lines, "timer=") == list(TIMER_NAMES)
    assert "libexec=/usr/local/libexec" in lines
    assert "systemctl=systemctl" in lines


def _write_fake_systemctl(tmp_path: Path) -> tuple[Path, Path, Path]:
    command_log = tmp_path / "systemctl-argv.bin"
    state_dir = tmp_path / "timer-state"
    state_dir.mkdir()
    systemctl = tmp_path / "systemctl"
    systemctl.write_text(
        """#!/usr/bin/env bash
set -u
printf '%s\\0' "$@" >> "$FAKE_SYSTEMCTL_LOG"
printf '\\0' >> "$FAKE_SYSTEMCTL_LOG"
case "$1" in
  is-enabled)
    value="$(cat "$FAKE_SYSTEMCTL_STATE_DIR/$2.enabled")"
    printf '%s\\n' "$value"
    [[ "$value" == enabled ]] && exit 0 || exit 1
    ;;
  is-active)
    value="$(cat "$FAKE_SYSTEMCTL_STATE_DIR/$2.active")"
    printf '%s\\n' "$value"
    [[ "$value" == active ]] && exit 0 || exit 3
    ;;
  daemon-reload)
    count=0
    [[ -f "$FAKE_SYSTEMCTL_STATE_DIR/reload-count" ]] &&
      count="$(cat \
        "$FAKE_SYSTEMCTL_STATE_DIR/reload-count")"
    count=$((count + 1))
    printf '%s' "$count" > "$FAKE_SYSTEMCTL_STATE_DIR/reload-count"
    if [[ "${FAKE_FAIL_FIRST_RELOAD:-0}" == 1 && "$count" == 1 ]]; then
      echo 'daemon reload failed' >&2
      exit 71
    fi
    ;;
  enable|disable)
    printf '%s' "${1}d" > "$FAKE_SYSTEMCTL_STATE_DIR/$2.enabled"
    ;;
  start|stop)
    if [[ "$1" == start ]]; then printf active > \
      "$FAKE_SYSTEMCTL_STATE_DIR/$2.active"; else printf inactive > \
      "$FAKE_SYSTEMCTL_STATE_DIR/$2.active"; fi
    ;;
esac
""",
        encoding="utf-8",
    )
    systemctl.chmod(0o755)
    return systemctl, command_log, state_dir


@dataclass(frozen=True)
class InstallerSandbox:
    systemctl: Path
    command_log: Path
    state_dir: Path
    destinations: list[Path]


def _prepare_installer(
    tmp_path: Path,
    timer_states: tuple[tuple[str, str], tuple[str, str]],
    source_prefix: str,
) -> InstallerSandbox:
    systemctl, command_log, state_dir = _write_fake_systemctl(tmp_path)
    sources = [tmp_path / f"source-{index}" for index in range(5)]
    for index, source in enumerate(sources):
        source.write_bytes(f"{source_prefix} {index}\n".encode())
        source.chmod(0o600)
    libexec_dir = tmp_path / "libexec"
    destinations = [
        libexec_dir / "skriptoteket-cleanup-if-running",
        *(tmp_path / f"unit-{index}" for index in range(1, 5)),
    ]
    for timer, states in zip(TIMER_NAMES, timer_states, strict=True):
        (state_dir / f"{timer}.enabled").write_text(states[0], encoding="utf-8")
        (state_dir / f"{timer}.active").write_text(states[1], encoding="utf-8")
    return InstallerSandbox(systemctl, command_log, state_dir, destinations)


def _run_installer(
    sandbox: InstallerSandbox, fail_first_reload: bool
) -> subprocess.CompletedProcess[str]:
    tmp_path = sandbox.state_dir.parent
    libexec_dir = sandbox.destinations[0].parent
    return _run_bash(
        """source "$1"
sources=("$4/source-0" "$4/source-1" "$4/source-2" "$4/source-3" "$4/source-4")
destinations=("$5/skriptoteket-cleanup-if-running" "$4/unit-1" "$4/unit-2" "$4/unit-3" "$4/unit-4")
modes=(0755 0644 0644 0644 0644)
timers=(skriptoteket-session-files-cleanup.timer skriptoteket-sandbox-snapshots-cleanup.timer)
libexec_dir="$5"
systemctl_command=("$2")
id() { printf '0\\n'; }
main
        """,
        str(INSTALLER),
        str(sandbox.systemctl),
        str(sandbox.state_dir),
        str(tmp_path),
        str(libexec_dir),
        environment={
            "FAKE_SYSTEMCTL_LOG": str(sandbox.command_log),
            "FAKE_SYSTEMCTL_STATE_DIR": str(sandbox.state_dir),
            "FAKE_FAIL_FIRST_RELOAD": "1" if fail_first_reload else "0",
        },
    )


@pytest.mark.parametrize(
    "timer_states",
    [
        (("enabled", "active"), ("disabled", "inactive")),
        (("disabled", "inactive"), ("enabled", "active")),
    ],
)
def test_installer_copies_exact_bytes_modes_and_preserves_timer_states(
    tmp_path: Path,
    timer_states: tuple[tuple[str, str], tuple[str, str]],
) -> None:
    sandbox = _prepare_installer(tmp_path, timer_states, "source bytes")
    result = _run_installer(sandbox, fail_first_reload=False)
    calls = _docker_calls(sandbox.command_log)

    assert result.returncode == 0
    assert "Installed cleanup destinations:" in result.stdout
    assert [destination.read_bytes() for destination in sandbox.destinations] == [
        f"source bytes {index}\n".encode() for index in range(5)
    ]
    assert [
        stat.S_IMODE(destination.stat().st_mode) for destination in sandbox.destinations
    ] == INSTALLED_FILE_MODES
    assert calls.count(["daemon-reload"]) == 1
    assert all(call[0] not in {"enable", "disable", "start", "stop"} for call in calls)
    for timer, expected in zip(TIMER_NAMES, timer_states, strict=True):
        assert (sandbox.state_dir / f"{timer}.enabled").read_text(encoding="utf-8") == expected[0]
        assert (sandbox.state_dir / f"{timer}.active").read_text(encoding="utf-8") == expected[1]


def test_installer_rolls_back_after_reload_failure(tmp_path: Path) -> None:
    states = (("enabled", "active"), ("disabled", "inactive"))
    sandbox = _prepare_installer(tmp_path, states, "replacement")
    original_bytes = [f"original {index}\n".encode() for index in range(1, 5)]
    original_modes = [0o600, 0o640, 0o644, 0o700]
    for destination, content, mode in zip(
        sandbox.destinations[1:], original_bytes, original_modes, strict=True
    ):
        destination.write_bytes(content)
        destination.chmod(mode)
    result = _run_installer(sandbox, fail_first_reload=True)
    calls = _docker_calls(sandbox.command_log)
    assert result.returncode == 71
    assert "daemon reload failed" in result.stderr
    assert not sandbox.destinations[0].exists()
    assert [destination.read_bytes() for destination in sandbox.destinations[1:]] == original_bytes
    assert [
        stat.S_IMODE(destination.stat().st_mode) for destination in sandbox.destinations[1:]
    ] == original_modes
    assert calls.count(["daemon-reload"]) == 2
    assert [call[:2] for call in calls if call[0] in {"enable", "disable", "start", "stop"}] == [
        ["enable", TIMER_NAMES[0]],
        ["start", TIMER_NAMES[0]],
        ["disable", TIMER_NAMES[1]],
        ["stop", TIMER_NAMES[1]],
    ]
    for timer, expected in zip(TIMER_NAMES, states, strict=True):
        assert (sandbox.state_dir / f"{timer}.enabled").read_text(encoding="utf-8") == expected[0]
        assert (sandbox.state_dir / f"{timer}.active").read_text(encoding="utf-8") == expected[1]
