import os
import shutil
import subprocess
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
HELPER = REPOSITORY_ROOT / "scripts" / "pre_push_touches_migrations.sh"
HOOK = REPOSITORY_ROOT / "scripts" / "hemma_pre_push_check.sh"
ZEROES = "0" * 40


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "commit.gpgsign", "false")
    (repo / "base.txt").write_text("base\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "base")


def _repo_with_change(tmp_path: Path, relpath: str) -> tuple[str, str, Path]:
    repo = tmp_path / "repo"
    _init_repo(repo)
    frm = _git(repo, "rev-parse", "HEAD")
    target = repo / relpath
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("changed\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", f"change {relpath}")
    to = _git(repo, "rev-parse", "HEAD")
    return frm, to, repo


def _run_helper(frm: str, to: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(HELPER), frm, to],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )


def test_docs_only_range_does_not_touch_migrations(tmp_path: Path) -> None:
    frm, to, repo = _repo_with_change(tmp_path, "docs/x.md")
    result = _run_helper(frm, to, repo)
    assert result.returncode == 0
    assert result.stdout.strip() == "skip"


def test_migration_version_range_touches_migrations(tmp_path: Path) -> None:
    frm, to, repo = _repo_with_change(tmp_path, "migrations/versions/abc_x.py")
    result = _run_helper(frm, to, repo)
    assert result.returncode == 0
    assert result.stdout.strip() == "run"


def test_migration_test_range_touches_migrations(tmp_path: Path) -> None:
    frm, to, repo = _repo_with_change(
        tmp_path, "tests/integration/test_migration_abc_idempotent.py"
    )
    result = _run_helper(frm, to, repo)
    assert result.returncode == 0
    assert result.stdout.strip() == "run"


def test_migration_support_module_range_touches_migrations(tmp_path: Path) -> None:
    frm, to, repo = _repo_with_change(
        tmp_path, "tests/integration/migration_idempotency_support.py"
    )
    result = _run_helper(frm, to, repo)
    assert result.returncode == 0
    assert result.stdout.strip() == "run"


def test_database_fixtures_range_touches_migrations(tmp_path: Path) -> None:
    frm, to, repo = _repo_with_change(tmp_path, "tests/fixtures/database_fixtures.py")
    result = _run_helper(frm, to, repo)
    assert result.returncode == 0
    assert result.stdout.strip() == "run"


def test_source_only_range_does_not_touch_migrations(tmp_path: Path) -> None:
    frm, to, repo = _repo_with_change(tmp_path, "src/skriptoteket/x.py")
    result = _run_helper(frm, to, repo)
    assert result.returncode == 0
    assert result.stdout.strip() == "skip"


def test_unknown_from_ref_is_an_error(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    to = _git(repo, "rev-parse", "HEAD")
    missing = "f" * 40
    assert missing != to
    result = _run_helper(missing, to, repo)
    assert result.returncode != 0
    assert result.stdout == ""


def _repo_with_rename(tmp_path: Path, src_relpath: str, dst_relpath: str) -> tuple[str, str, Path]:
    repo = tmp_path / "repo"
    _init_repo(repo)
    src = repo / src_relpath
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text("content\n" * 50, encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", f"add {src_relpath}")
    frm = _git(repo, "rev-parse", "HEAD")
    dst = repo / dst_relpath
    dst.parent.mkdir(parents=True, exist_ok=True)
    _git(repo, "mv", src_relpath, dst_relpath)
    _git(repo, "commit", "-m", f"move {src_relpath} to {dst_relpath}")
    to = _git(repo, "rev-parse", "HEAD")
    return frm, to, repo


def test_rename_out_of_migrations_runs(tmp_path: Path) -> None:
    frm, to, repo = _repo_with_rename(tmp_path, "migrations/versions/abc_x.py", "archived/abc_x.py")
    status = _git(repo, "diff", "--name-status", frm, to)
    assert status.startswith("R")
    result = _run_helper(frm, to, repo)
    assert result.returncode == 0
    assert result.stdout.strip() == "run"


def test_rename_of_migration_test_runs(tmp_path: Path) -> None:
    frm, to, repo = _repo_with_rename(
        tmp_path,
        "tests/integration/test_migration_abc_idempotent.py",
        "tests/other/x.py",
    )
    status = _git(repo, "diff", "--name-status", frm, to)
    assert status.startswith("R")
    result = _run_helper(frm, to, repo)
    assert result.returncode == 0
    assert result.stdout.strip() == "run"


ADAPTER_CONFIG = """\
repos:
  - repo: local
    hooks:
      - id: hemma-pre-push-check
        name: hemma-pre-push-check
        entry: scripts/hemma_pre_push_check.sh
        language: system
        stages: [pre-push]
        always_run: true
        pass_filenames: false
        verbose: true
"""


def _adapter_repo(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "adapter"
    _init_repo(repo)
    scripts = repo / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    shutil.copy(HELPER, scripts / "pre_push_touches_migrations.sh")
    shutil.copy(HOOK, scripts / "hemma_pre_push_check.sh")
    (repo / ".pre-commit-config.yaml").write_text(ADAPTER_CONFIG, encoding="utf-8")
    bindir = tmp_path / "bin"
    bindir.mkdir(parents=True, exist_ok=True)
    stub = bindir / "ssh"
    stub.write_text("#!/usr/bin/env bash\nexit 255\n", encoding="utf-8")
    stub.chmod(0o755)
    hook_dir = repo / ".git" / "hooks"
    hook_dir.mkdir(parents=True, exist_ok=True)
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "adapter setup")
    return repo, bindir


def _run_adapter(
    repo: Path,
    bindir: Path,
    local_ref: str,
    local_sha: str,
    remote_ref: str,
    remote_sha: str,
) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PATH"] = f"{bindir}{os.pathsep}{env['PATH']}"
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "pre_commit",
            "hook-impl",
            "--config=.pre-commit-config.yaml",
            "--hook-type=pre-push",
            "--hook-dir",
            str(repo / ".git" / "hooks"),
            "--",
            "origin",
            "git@example.com:test.git",
        ],
        input=f"{local_ref} {local_sha} {remote_ref} {remote_sha}\n",
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
    )


def test_adapter_first_push_runs_migrations(tmp_path: Path) -> None:
    repo, bindir = _adapter_repo(tmp_path)
    local_sha = _git(repo, "rev-parse", "HEAD")
    result = _run_adapter(repo, bindir, "refs/heads/main", local_sha, "refs/heads/main", ZEROES)
    combined = result.stdout + result.stderr
    assert result.returncode == 0
    assert "docker migration tests will run" in combined
    assert "Hemma unreachable" in combined


def test_adapter_docs_only_push_skips_migrations(tmp_path: Path) -> None:
    repo, bindir = _adapter_repo(tmp_path)
    first = _git(repo, "rev-parse", "HEAD")
    (repo / "docs").mkdir(exist_ok=True)
    (repo / "docs" / "x.md").write_text("docs\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "docs change")
    second = _git(repo, "rev-parse", "HEAD")
    _git(repo, "update-ref", "refs/remotes/origin/main", first)
    result = _run_adapter(repo, bindir, "refs/heads/main", second, "refs/heads/main", first)
    combined = result.stdout + result.stderr
    assert result.returncode == 0
    assert "docker migration tests will run" not in combined
    assert "Hemma unreachable" in combined


def test_adapter_migration_push_runs_migrations(tmp_path: Path) -> None:
    repo, bindir = _adapter_repo(tmp_path)
    first = _git(repo, "rev-parse", "HEAD")
    target = repo / "migrations" / "versions" / "abc_x.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("migration\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "migration change")
    second = _git(repo, "rev-parse", "HEAD")
    _git(repo, "update-ref", "refs/remotes/origin/main", first)
    result = _run_adapter(repo, bindir, "refs/heads/main", second, "refs/heads/main", first)
    combined = result.stdout + result.stderr
    assert result.returncode == 0
    assert "docker migration tests will run" in combined
    assert "Hemma unreachable" in combined
