"""Unit tests for the Hemma deploy launcher scripts/hemma_deploy_start.sh.

Purpose:
    Prove that the launcher accepts only its two named modes and no checkout
    selector, always targets the fixed production checkout, syncs it to
    origin/main, and opens the mode's worker under
    `agent-secrets run --set skriptoteket-prod` only when the checkout is its
    own Git root, HEAD equals the fetched main and the worker is tracked.
    Every refusal happens before agent-secrets is called.

Relationships:
    - Runs the real launcher with stubbed `ssh` and `agent-secrets`
      executables that record argv. The ssh stub maps the fixed production
      path to a synthetic checkout cloned from a local origin, and a `git`
      stub records argv and runs the real git there.
    - The workers' own secrets handling is covered in
      test_hemma_deploy_scripts_secrets.py.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
PRODUCTION_CHECKOUT = "/home/paunchygent/apps/skriptoteket"
SCRIPTS = (
    "hemma_deploy_and_verify_seating_export.sh",
    "hemma_deploy_and_verify_share_previews.sh",
)
GIT_IDENTITY = {
    "GIT_AUTHOR_NAME": "test",
    "GIT_AUTHOR_EMAIL": "test@example.invalid",
    "GIT_COMMITTER_NAME": "test",
    "GIT_COMMITTER_EMAIL": "test@example.invalid",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
}


def _write_stub(directory: Path, name: str, body: str) -> None:
    stub = directory / name
    stub.write_text(body, encoding="utf-8")
    stub.chmod(0o755)


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


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=cwd,
        env={**os.environ, **GIT_IDENTITY},
        check=True,
        capture_output=True,
    )


def _make_checkout(tmp_path: Path, *, tracked: tuple[str, ...], branch: str) -> Path:
    """Create an origin with the tracked workers and a clone of it, with every
    worker file present in the clone (untracked ones only on disk)."""
    origin = tmp_path / "origin"
    origin.mkdir()
    _git(origin, "init", "-q", "-b", "main")
    (origin / "scripts").mkdir()
    for script_name in SCRIPTS:
        if script_name in tracked:
            (origin / "scripts" / script_name).write_text(
                f'#!/usr/bin/env bash\nprintf "worker\\0{script_name}\\0\\0" >>"$CALLS"\nsleep 2\n',
                encoding="utf-8",
            )
    (origin / "README").write_text("origin\n", encoding="utf-8")
    _git(origin, "add", ".")
    _git(origin, "commit", "-q", "-m", "workers")
    checkout = tmp_path / "remote"
    _git(tmp_path, "clone", "-q", str(origin), str(checkout))
    for script_name in SCRIPTS:
        if script_name not in tracked:
            (checkout / "scripts" / script_name).write_text(
                f'#!/usr/bin/env bash\nprintf "worker\\0{script_name}\\0\\0" >>"$CALLS"\n',
                encoding="utf-8",
            )
    if branch != "main":
        _git(checkout, "checkout", "-q", "-b", branch)
    return checkout


def _run_launcher(
    tmp_path: Path,
    *args: str,
    remote_branch: str = "main",
    tracked: tuple[str, ...] = SCRIPTS,
    ssh_target: Callable[[Path], Path] | None = None,
    ahead_of_origin: bool = False,
) -> tuple[subprocess.CompletedProcess[str], list[list[str]], Path]:
    """Run hemma_deploy_start.sh with ssh mapping the fixed production path to
    a synthetic checkout (or to `ssh_target` inside it)."""
    checkout = _make_checkout(tmp_path, tracked=tracked, branch=remote_branch)
    if ahead_of_origin:
        (checkout / "local.txt").write_text("local\n", encoding="utf-8")
        _git(checkout, "add", "local.txt")
        _git(checkout, "commit", "-q", "-m", "local commit")
    target = checkout if ssh_target is None else ssh_target(checkout)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    calls_log = tmp_path / "calls.bin"
    calls_log.touch()
    real_git = shutil.which("git")
    assert real_git is not None
    record = (
        "#!/usr/bin/env bash\nprintf '{name}\\0' >>\"$CALLS\"\n"
        'printf \'%s\\0\' "$@" >>"$CALLS"\nprintf \'\\0\' >>"$CALLS"\n'
    )
    _write_stub(
        bin_dir,
        "ssh",
        record.format(name="ssh")
        + 'shift\n[[ "$1" == "/bin/bash" && "$2" == "-s" && "$3" == "--" ]] || exit 92\n'
        f'shift 3\n[[ "$1" == "{PRODUCTION_CHECKOUT}" ]] || exit 93\n'
        'shift\nexec bash -s -- "$SSH_TARGET" "$@"\n',
    )
    _write_stub(bin_dir, "git", record.format(name="git") + f'exec "{real_git}" "$@"\n')
    _write_stub(
        bin_dir, "agent-secrets", record.format(name="agent-secrets") + 'shift 4\nexec "$@"\n'
    )

    env = {key: value for key, value in os.environ.items() if key != "AGENT_SECRETS_VARIABLES"}
    env.update(GIT_IDENTITY)
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["CALLS"] = str(calls_log)
    env["SSH_TARGET"] = str(target)
    result = subprocess.run(
        [
            "bash",
            str(REPOSITORY_ROOT / "scripts" / "hemma_deploy_start.sh"),
            "--host",
            "unused",
            *args,
        ],
        check=False,
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )
    return result, _calls(calls_log), checkout


@pytest.mark.parametrize("remote_branch", ["main", "task-branch"])
@pytest.mark.parametrize(
    ("mode_args", "script_name"),
    [
        ((), "hemma_deploy_and_verify_seating_export.sh"),
        (("--mode", "seating-export"), "hemma_deploy_and_verify_seating_export.sh"),
        (("--mode", "share-previews"), "hemma_deploy_and_verify_share_previews.sh"),
    ],
)
def test_start_script_syncs_then_opens_tracked_worker_at_git_root_under_production_set(
    tmp_path: Path, remote_branch: str, mode_args: tuple[str, ...], script_name: str
) -> None:
    """The launcher fast-forwards origin/main in the fixed checkout and then
    starts the mode's tracked worker from the Git root under the production
    set."""
    result, calls, checkout = _run_launcher(tmp_path, *mode_args, remote_branch=remote_branch)

    assert result.returncode == 0, result.stderr + result.stdout
    ssh_call = next(call for call in calls if call[0] == "ssh")
    assert ssh_call[5] == PRODUCTION_CHECKOUT
    fetch_index = next(i for i, call in enumerate(calls) if call[:2] == ["git", "fetch"])
    pull_index = next(i for i, call in enumerate(calls) if call[:3] == ["git", "pull", "--ff-only"])
    agent_index = next(i for i, call in enumerate(calls) if call[0] == "agent-secrets")
    worker_index = next(i for i, call in enumerate(calls) if call[0] == "worker")
    assert fetch_index < pull_index < agent_index < worker_index
    assert calls[agent_index][1:] == [
        "run",
        "--set",
        "skriptoteket-prod",
        "--",
        "/bin/bash",
        str(checkout.resolve() / "scripts" / script_name),
    ]
    assert calls[worker_index] == ["worker", script_name]
    if remote_branch != "main":
        checkout_index = next(
            i for i, call in enumerate(calls) if call[:3] == ["git", "checkout", "main"]
        )
        assert checkout_index < fetch_index


@pytest.mark.parametrize(
    "args",
    [
        ("--mode", "rollback"),
        ("--mode", "scripts/hemma_deploy_and_verify_share_previews.sh"),
        ("--mode", "/tmp/old_worker.sh"),
        ("--mode",),
        ("--script", "scripts/hemma_deploy_and_verify_share_previews.sh"),
        ("--repo-dir", f"{PRODUCTION_CHECKOUT}/saved-tree"),
    ],
)
def test_start_script_refuses_anything_but_named_modes_before_ssh(
    tmp_path: Path, args: tuple[str, ...]
) -> None:
    """Only the two named modes select a worker: an unknown mode, a path, the
    removed --script option and the removed --repo-dir option exit 1 before
    ssh or any store lookup."""
    result, calls, _ = _run_launcher(tmp_path, *args)

    assert result.returncode == 1
    assert "Unknown" in result.stderr
    assert calls == []


def test_start_script_refuses_main_ahead_of_fetched_origin(tmp_path: Path) -> None:
    """A local main with commits origin lacks does not deploy."""
    result, calls, _ = _run_launcher(tmp_path, ahead_of_origin=True)

    assert result.returncode == 1
    assert "differs from the fetched origin/main" in result.stderr
    assert not any(call[0] in {"agent-secrets", "worker"} for call in calls)


def test_start_script_refuses_untracked_worker(tmp_path: Path) -> None:
    """A worker file present on disk but not tracked at the synced revision
    does not receive the production set."""
    result, calls, _ = _run_launcher(tmp_path, "--mode", "share-previews", tracked=(SCRIPTS[0],))

    assert result.returncode == 1
    assert "is not tracked" in result.stderr
    assert not any(call[0] in {"agent-secrets", "worker"} for call in calls)


def test_start_script_refuses_checkout_that_is_not_its_git_root(tmp_path: Path) -> None:
    """If the fixed path resolves to a directory inside another repository,
    the launcher refuses instead of syncing and using the enclosing one."""
    result, calls, _ = _run_launcher(tmp_path, ssh_target=lambda checkout: checkout / "scripts")

    assert result.returncode == 1
    assert "is not the root of its Git worktree" in result.stderr
    assert not any(call[:2] in (["git", "fetch"], ["git", "pull"]) for call in calls)
    assert not any(call[0] in {"agent-secrets", "worker"} for call in calls)
