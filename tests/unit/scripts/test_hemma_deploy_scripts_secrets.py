"""Unit tests for the Hemma production deploy scripts' secrets wrapping.

Purpose:
    Prove that scripts/hemma_deploy_and_verify_*.sh run their compose `up` and
    `build` paths through `agent-secrets run --set skriptoteket-prod` with
    `sudo --preserve-env` and the compose.secrets.prod.yaml overlay, keep `exec`
    on the base file, and take secrets from the set rather than `.env`.

Relationships:
    - Exercises the real scripts in a sandboxed checkout with stubbed
      `agent-secrets`, `sudo`, `docker` and `git` executables that record argv
      and emulate `agent-secrets run` injection and `sudo env_reset`.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = (
    "hemma_deploy_and_verify_seating_export.sh",
    "hemma_deploy_and_verify_share_previews.sh",
)
SET_VARIABLES = (
    "BOOTSTRAP_SUPERUSER_PASSWORD",
    "EMAIL_SMTP_PASSWORD",
    "GRAFANA_ADMIN_PASSWORD",
    "HULEEDU_INTERNAL_API_KEY",
    "SECRET_KEY",
    "SIR_CONVERT_A_LOT_V2_API_KEY",
    "SKRIPTOTEKET_DB_PASSWORD",
)
SET_CSV = ",".join(SET_VARIABLES)


def _write_stub(directory: Path, name: str, body: str) -> None:
    stub = directory / name
    stub.write_text(body, encoding="utf-8")
    stub.chmod(0o755)


def _prepare_sandbox(tmp_path: Path, script_name: str) -> tuple[Path, Path, Path]:
    """Copy the deploy script into a fake checkout with stub executables."""
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    script = scripts_dir / script_name
    script.write_text((REPOSITORY_ROOT / "scripts" / script_name).read_text(encoding="utf-8"))

    keys_dir = tmp_path / "keys"
    keys_dir.mkdir()
    (keys_dir / "gateway-internal-identity-public-key.pem").write_text(
        "test-key\n", encoding="utf-8"
    )

    # .env keeps configuration; decoy secret values prove the set wins.
    (tmp_path / ".env").write_text(
        "\n".join(
            [
                "BOOTSTRAP_SUPERUSER_EMAIL=admin@example.com",
                f"HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY_HOST_DIR={keys_dir}",
                "SECRET_KEY=dotenv-secret-key",
                "BOOTSTRAP_SUPERUSER_PASSWORD=dotenv-password",
                "SKRIPTOTEKET_DB_PASSWORD=dotenv-db-password",
                "",
            ]
        ),
        encoding="utf-8",
    )

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    calls = tmp_path / "calls.bin"
    env_log = tmp_path / "env.log"

    _write_stub(
        bin_dir,
        "agent-secrets",
        """#!/usr/bin/env bash
printf 'agent-secrets\\0' >>"$CALLS"
printf '%s\\0' "$@" >>"$CALLS"
printf '\\0' >>"$CALLS"
[[ "$1" == run ]] || exit 90
shift
set_name=""
while [[ $# -gt 0 && "$1" != "--" ]]; do
  if [[ "$1" == "--set" ]]; then set_name="$2"; shift 2; else shift; fi
done
[[ "$1" == "--" ]] && shift
[[ "$set_name" == "skriptoteket-prod" ]] || { echo "unexpected set: $set_name" >&2; exit 91; }
export BOOTSTRAP_SUPERUSER_PASSWORD=set-bootstrap-password
export EMAIL_SMTP_PASSWORD=set-smtp-password
export GRAFANA_ADMIN_PASSWORD=set-grafana-password
export HULEEDU_INTERNAL_API_KEY=set-huleedu-key
export SECRET_KEY=set-secret-key
export SIR_CONVERT_A_LOT_V2_API_KEY=set-sir-key
export SKRIPTOTEKET_DB_PASSWORD=set-db-password
export AGENT_SECRETS_VARIABLES="BOOTSTRAP_SUPERUSER_PASSWORD,EMAIL_SMTP_PASSWORD"
AGENT_SECRETS_VARIABLES+=",GRAFANA_ADMIN_PASSWORD,HULEEDU_INTERNAL_API_KEY"
AGENT_SECRETS_VARIABLES+=",SECRET_KEY,SIR_CONVERT_A_LOT_V2_API_KEY,SKRIPTOTEKET_DB_PASSWORD"
exec "$@"
""",
    )
    _write_stub(
        bin_dir,
        "sudo",
        """#!/usr/bin/env bash
printf 'sudo\\0' >>"$CALLS"
printf '%s\\0' "$@" >>"$CALLS"
printf '\\0' >>"$CALLS"
args=()
preserve=""
for arg in "$@"; do
  if [[ "$arg" == --preserve-env=* ]]; then
    preserve="${arg#--preserve-env=}"
  else
    args+=("$arg")
  fi
done
if [[ -n "${AGENT_SECRETS_VARIABLES:-}" ]]; then
  IFS=',' read -ra keep <<<"$preserve"
  for name in ${AGENT_SECRETS_VARIABLES//,/ }; do
    keep_it=0
    for k in "${keep[@]}"; do [[ "$k" == "$name" ]] && keep_it=1; done
    (( keep_it )) || unset "$name"
  done
fi
unset AGENT_SECRETS_VARIABLES
exec "${args[@]}"
""",
    )
    _write_stub(
        bin_dir,
        "docker",
        """#!/usr/bin/env bash
printf 'docker\\0' >>"$CALLS"
printf '%s\\0' "$@" >>"$CALLS"
printf '\\0' >>"$CALLS"
printf 'SECRET_KEY=%s SKRIPTOTEKET_DB_PASSWORD=%s\\n' \
  "${SECRET_KEY-<unset>}" "${SKRIPTOTEKET_DB_PASSWORD-<unset>}" >>"$ENVLOG"
exit 0
""",
    )
    _write_stub(
        bin_dir,
        "git",
        """#!/usr/bin/env bash
printf 'git\\0' >>"$CALLS"
printf '%s\\0' "$@" >>"$CALLS"
printf '\\0' >>"$CALLS"
if [[ "$1" == "rev-parse" ]]; then
  if [[ "$2" == "--abbrev-ref" ]]; then echo main; else echo deadbeef; fi
fi
exit 0
""",
    )
    return script, calls, env_log


def _calls(log: Path) -> list[list[str]]:
    entries: list[list[str]] = []
    current: list[str] = []
    for chunk in log.read_bytes().split(b"\0"):
        if chunk:
            current.append(chunk.decode("utf-8"))
        elif current:
            entries.append(current)
            current = []
    return entries


def _run_script(
    script: Path, tmp_path: Path, calls: Path, env_log: Path
) -> subprocess.CompletedProcess[str]:
    env = {key: value for key, value in os.environ.items() if key != "AGENT_SECRETS_VARIABLES"}
    env["PATH"] = f"{tmp_path / 'bin'}:{env['PATH']}"
    env["CALLS"] = str(calls)
    env["ENVLOG"] = str(env_log)
    return subprocess.run(
        ["bash", str(script)],
        check=False,
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )


def _compose_files(call: list[str]) -> list[str]:
    return [call[index + 1] for index, part in enumerate(call[:-1]) if part == "-f"]


@pytest.mark.parametrize("script_name", SCRIPTS)
def test_deploy_runs_through_agent_secrets_and_passes_overlay_only_to_creating_paths(
    tmp_path: Path, script_name: str
) -> None:
    script, calls_log, env_log = _prepare_sandbox(tmp_path, script_name)

    result = _run_script(script, tmp_path, calls_log, env_log)

    assert result.returncode == 0, result.stderr
    calls = _calls(calls_log)

    agent_calls = [call[1:] for call in calls if call[0] == "agent-secrets"]
    assert agent_calls == [["run", "--set", "skriptoteket-prod", "--", "bash", str(script)]]

    docker_calls = [call[1:] for call in calls if call[0] == "docker"]
    sudo_calls = [call[1:] for call in calls if call[0] == "sudo"]

    creating = [call for call in docker_calls if any(verb in call for verb in ("up", "build"))]
    assert creating, "expected at least one compose up/build call"
    for call in creating:
        assert _compose_files(call) == ["compose.prod.yaml", "compose.secrets.prod.yaml"]

    exec_compose = [
        call for call in docker_calls if call[:2] == ["compose", "-f"] and "exec" in call
    ]
    assert exec_compose, "expected at least one compose exec call"
    for call in exec_compose:
        assert _compose_files(call) == ["compose.prod.yaml"]

    # sudo ran the overlay paths with --preserve-env carrying the whole set, and
    # env_reset dropped the set for base-file paths.
    assert any(f"--preserve-env={SET_CSV}" in call for call in sudo_calls)
    env_lines = env_log.read_text(encoding="utf-8").splitlines()
    assert len(env_lines) == len(docker_calls)
    for call, env_line in zip(docker_calls, env_lines, strict=True):
        # The scratch .env holds dotenv-* decoys for both names; the value the
        # stub agent-secrets injects overwrites them, so the decoys never reach
        # docker and the set value wins on the overlay paths.
        assert "dotenv" not in env_line
        if "compose.secrets.prod.yaml" in call:
            assert "SECRET_KEY=set-secret-key" in env_line
            assert "SKRIPTOTEKET_DB_PASSWORD=set-db-password" in env_line
        elif "compose" in call:
            assert "SECRET_KEY=<unset>" in env_line


def test_seating_export_smoke_takes_bootstrap_password_from_the_set(tmp_path: Path) -> None:
    script, calls_log, env_log = _prepare_sandbox(
        tmp_path, "hemma_deploy_and_verify_seating_export.sh"
    )

    result = _run_script(script, tmp_path, calls_log, env_log)

    assert result.returncode == 0, result.stderr
    calls = _calls(calls_log)
    docker_exec = [call for call in calls if call[0] == "docker" and call[1] == "exec"]
    assert len(docker_exec) == 1
    assert "-e" in docker_exec[0]
    assert "BOOTSTRAP_SUPERUSER_PASSWORD=set-bootstrap-password" in docker_exec[0]
    assert not any("dotenv" in part for call in calls for part in call)
