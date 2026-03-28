"""Unit tests for the pre-commit targeted pytest wrapper.

Purpose:
    Lock commit-time marker handling so excluded suites such as `simulation`
    do not break local commit hygiene through accidental deselection.
Relationships:
    - Exercises `scripts.run_precommit_targeted_unit_tests`
    - Verifies marker-aware skipping, targeted execution, and fallback behavior
"""

from __future__ import annotations

from pathlib import Path

from scripts import run_precommit_targeted_unit_tests as module


def _write_python_file(path: Path, contents: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents, encoding="utf-8")
    return path


def _configure_fake_repo(monkeypatch, tmp_path: Path) -> None:
    root = tmp_path.resolve()
    monkeypatch.setattr(module, "ROOT", root)
    monkeypatch.setattr(module, "TESTS_ROOT", root / "tests" / "unit")


def test_main_skips_simulation_marked_unit_tests(monkeypatch, tmp_path: Path, capsys) -> None:
    _configure_fake_repo(monkeypatch, tmp_path)
    simulation_test = _write_python_file(
        tmp_path / "tests" / "unit" / "domain" / "test_simulation_suite.py",
        "import pytest\n\npytestmark = pytest.mark.simulation\n",
    )
    subprocess_calls: list[tuple[list[str], Path, bool]] = []

    def _fake_run(command: list[str], cwd: Path, check: bool) -> object:
        subprocess_calls.append((command, cwd, check))
        raise AssertionError("subprocess.run should not be called for excluded simulation tests")

    monkeypatch.setattr(module.subprocess, "run", _fake_run)

    result = module.main([str(simulation_test.relative_to(tmp_path))])

    captured = capsys.readouterr()
    assert result == 0
    assert subprocess_calls == []
    assert "skipping tests/unit/domain/test_simulation_suite.py" in captured.out
    assert "run `pdm run test-simulations`" in captured.out


def test_main_runs_non_excluded_unit_tests(monkeypatch, tmp_path: Path, capsys) -> None:
    _configure_fake_repo(monkeypatch, tmp_path)
    fast_test = _write_python_file(
        tmp_path / "tests" / "unit" / "domain" / "test_fast_suite.py",
        "def test_ok() -> None:\n    assert True\n",
    )
    subprocess_calls: list[tuple[list[str], Path, bool]] = []

    class _Completed:
        returncode = 0

    def _fake_run(command: list[str], cwd: Path, check: bool) -> _Completed:
        subprocess_calls.append((command, cwd, check))
        return _Completed()

    monkeypatch.setattr(module.subprocess, "run", _fake_run)

    result = module.main([str(fast_test.relative_to(tmp_path))])

    captured = capsys.readouterr()
    assert result == 0
    assert subprocess_calls == [
        (
            ["pdm", "run", "pytest", "-q", "tests/unit/domain/test_fast_suite.py"],
            tmp_path.resolve(),
            False,
        )
    ]
    assert "running tests/unit/domain/test_fast_suite.py" in captured.out


def test_main_filters_out_excluded_inferred_tests_and_runs_fast_targets(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _configure_fake_repo(monkeypatch, tmp_path)
    source_file = _write_python_file(
        tmp_path / "src" / "skriptoteket" / "domain" / "planner.py",
        "def meaning() -> int:\n    return 42\n",
    )
    _write_python_file(
        tmp_path / "tests" / "unit" / "domain" / "test_planner.py",
        "def test_planner() -> None:\n    assert True\n",
    )
    _write_python_file(
        tmp_path / "tests" / "unit" / "domain" / "test_planner_simulation.py",
        "import pytest\n\npytestmark = pytest.mark.simulation\n",
    )
    subprocess_calls: list[list[str]] = []

    class _Completed:
        returncode = 0

    def _fake_run(command: list[str], cwd: Path, check: bool) -> _Completed:
        assert cwd == tmp_path.resolve()
        assert check is False
        subprocess_calls.append(command)
        return _Completed()

    monkeypatch.setattr(module.subprocess, "run", _fake_run)

    result = module.main([str(source_file.relative_to(tmp_path))])

    assert result == 0
    assert subprocess_calls == [["pdm", "run", "pytest", "-q", "tests/unit/domain/test_planner.py"]]


def test_main_skips_source_files_with_only_excluded_inferred_tests(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    _configure_fake_repo(monkeypatch, tmp_path)
    source_file = _write_python_file(
        tmp_path / "src" / "skriptoteket" / "domain" / "scheduler.py",
        "def schedule() -> None:\n    return None\n",
    )
    _write_python_file(
        tmp_path / "tests" / "unit" / "domain" / "test_scheduler_simulation.py",
        "import pytest\n\npytestmark = pytest.mark.simulation\n",
    )

    def _fake_run(*_args, **_kwargs) -> object:
        raise AssertionError(
            "subprocess.run should not be called when only excluded inferred tests exist"
        )

    monkeypatch.setattr(module.subprocess, "run", _fake_run)

    result = module.main([str(source_file.relative_to(tmp_path))])

    captured = capsys.readouterr()
    assert result == 0
    assert "test_scheduler_simulation.py" in captured.out
    assert "no unit-test-relevant Python files; skipping" in captured.out


def test_main_falls_back_to_tests_unit_when_no_mirrored_tests_exist(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _configure_fake_repo(monkeypatch, tmp_path)
    source_file = _write_python_file(
        tmp_path / "src" / "skriptoteket" / "application" / "orphans.py",
        "def orphan() -> str:\n    return 'ok'\n",
    )
    subprocess_calls: list[list[str]] = []

    class _Completed:
        returncode = 0

    def _fake_run(command: list[str], cwd: Path, check: bool) -> _Completed:
        assert cwd == tmp_path.resolve()
        assert check is False
        subprocess_calls.append(command)
        return _Completed()

    monkeypatch.setattr(module.subprocess, "run", _fake_run)

    result = module.main([str(source_file.relative_to(tmp_path))])

    assert result == 0
    assert subprocess_calls == [["pdm", "run", "pytest", "-q", "tests/unit"]]
