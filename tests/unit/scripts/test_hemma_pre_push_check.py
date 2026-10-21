import os
import shutil
import subprocess
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
HELPER = REPOSITORY_ROOT / "scripts" / "pre_push_touches_migrations.sh"
HOOK = REPOSITORY_ROOT / "scripts" / "hemma_pre_push_check.sh"

HOSTNAME_HEMMA = "paunchygent-server"


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


def _repo_with_source_change(tmp_path: Path, name: str) -> tuple[str, str, Path]:
    repo = tmp_path / name
    _init_repo(repo)
    scripts = repo / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    shutil.copy(HELPER, scripts / "pre_push_touches_migrations.sh")
    shutil.copy(HOOK, scripts / "hemma_pre_push_check.sh")
    target = repo / "src" / "app.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("print('hi')\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "source change")
    frm = _git(repo, "rev-parse", "HEAD~1")
    to = _git(repo, "rev-parse", "HEAD")
    return frm, to, repo


def _stage_doubles(bindir: Path, logdir: Path, real_git: str, ssh_exit: str) -> None:
    bindir.mkdir(parents=True, exist_ok=True)
    logdir.mkdir(parents=True, exist_ok=True)
    (bindir / "hostname").write_text(
        '#!/usr/bin/env bash\necho "${STUB_HOSTNAME:-%s}"\n' % HOSTNAME_HEMMA,
        encoding="utf-8",
    )
    (bindir / "git").write_text(
        "#!/usr/bin/env bash\n"
        'if [[ "${1:-}" == "checkout" ]]; then\n'
        '  echo "git $*" >>"$DOUBLE_LOG_DIR/git.log"\n'
        "  exit 0\n"
        "fi\n"
        'exec "$REAL_GIT" "$@"\n',
        encoding="utf-8",
    )
    (bindir / "pdm").write_text(
        '#!/usr/bin/env bash\necho "pdm $*" >>"$DOUBLE_LOG_DIR/pdm.log"\nexit 0\n',
        encoding="utf-8",
    )
    (bindir / "ssh").write_text(
        '#!/usr/bin/env bash\necho "ssh $*" >>"$DOUBLE_LOG_DIR/ssh.log"\nexit %s\n' % ssh_exit,
        encoding="utf-8",
    )
    (bindir / "flock").write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    for stub in ("hostname", "git", "pdm", "ssh", "flock"):
        (bindir / stub).chmod(0o755)


def _run_hook(
    repo: Path,
    bindir: Path,
    logdir: Path,
    fake_home: Path,
    real_git: str,
    hostname_value: str,
    frm: str,
    to: str,
) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PATH"] = f"{bindir}{os.pathsep}{env['PATH']}"
    env["HOME"] = str(fake_home)
    env["DOUBLE_LOG_DIR"] = str(logdir)
    env["REAL_GIT"] = real_git
    env["STUB_HOSTNAME"] = hostname_value
    env["PRE_COMMIT_REMOTE_BRANCH"] = "refs/heads/main"
    env["PRE_COMMIT_FROM_REF"] = frm
    env["PRE_COMMIT_TO_REF"] = to
    return subprocess.run(
        ["bash", "scripts/hemma_pre_push_check.sh"],
        cwd=repo,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )


def _prepare(
    tmp_path: Path, name: str, ssh_exit: str, hostname_value: str
) -> tuple[str, str, Path, Path, Path, Path, str]:
    frm, to, repo = _repo_with_source_change(tmp_path, name)
    bindir = tmp_path / f"{name}-bin"
    logdir = tmp_path / f"{name}-logs"
    fake_home = tmp_path / f"{name}-home"
    (fake_home / "apps" / "skriptoteket-verify-main").mkdir(parents=True, exist_ok=True)
    (fake_home / ".cache").mkdir(parents=True, exist_ok=True)
    real_git = shutil.which("git") or "git"
    _stage_doubles(bindir, logdir, real_git, ssh_exit)
    return frm, to, repo, bindir, logdir, fake_home, real_git


def test_on_hemma_runs_steps_directly_with_no_ssh(tmp_path: Path) -> None:
    frm, to, repo, bindir, logdir, fake_home, real_git = _prepare(
        tmp_path, "onhemma", ssh_exit="255", hostname_value=HOSTNAME_HEMMA
    )
    result = _run_hook(repo, bindir, logdir, fake_home, real_git, HOSTNAME_HEMMA, frm, to)
    combined = result.stdout + result.stderr
    assert result.returncode == 0, combined
    assert "directly on Hemma" in combined
    ssh_log_path = logdir / "ssh.log"
    ssh_log = ssh_log_path.read_text(encoding="utf-8") if ssh_log_path.exists() else ""
    assert ssh_log == "", f"ssh must not be called on Hemma, got: {ssh_log}"
    git_log = (logdir / "git.log").read_text(encoding="utf-8")
    assert f"checkout -q --detach {to}" in git_log
    pdm_log = (logdir / "pdm.log").read_text(encoding="utf-8")
    for step in (
        "pdm sync -q --clean",
        "pdm run fe-install --frozen-lockfile --silent",
        "pdm run fe-build",
        "pdm run typecheck",
        "pdm run test",
    ):
        assert step in pdm_log, f"missing {step!r} in pdm log:\n{pdm_log}"
    verified = (repo / ".git" / "hemma-verified-sha").read_text(encoding="utf-8").strip()
    assert verified == to
    assert "UNVERIFIED" not in combined


def test_unverifiable_push_is_refused(tmp_path: Path) -> None:
    frm, to, repo, bindir, logdir, fake_home, real_git = _prepare(
        tmp_path, "offhemma", ssh_exit="255", hostname_value="macbook-pro"
    )
    result = _run_hook(repo, bindir, logdir, fake_home, real_git, "macbook-pro", frm, to)
    combined = result.stdout + result.stderr
    assert result.returncode != 0, combined
    assert "push blocked" in combined
    assert "UNVERIFIED" not in combined
    assert not (repo / ".git" / "hemma-verified-sha").exists()
