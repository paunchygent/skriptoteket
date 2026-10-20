import subprocess
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
HELPER = REPOSITORY_ROOT / "scripts" / "pre_push_touches_migrations.sh"
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


def test_new_remote_ref_touches_migrations(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    to = _git(repo, "rev-parse", "HEAD")
    result = _run_helper(ZEROES, to, repo)
    assert result.returncode == 0
    assert result.stdout.strip() == "run"


def test_unknown_from_ref_is_an_error(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    to = _git(repo, "rev-parse", "HEAD")
    missing = "f" * 40
    assert missing != to
    result = _run_helper(missing, to, repo)
    assert result.returncode != 0
    assert result.stdout == ""
