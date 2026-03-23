"""Run fast staged-file unit tests for pre-commit.

This script keeps the commit-time pytest hook scoped to unit coverage that is
relevant to the changed Python files. It accepts file paths from pre-commit
when available and falls back to staged files from git for direct/manual runs.
When a changed source file has no obvious mirrored unit test, the script falls
back to the whole `tests/unit` suite instead of silently skipping coverage.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS_ROOT = ROOT / "tests" / "unit"
PYTEST_COMMAND = ["pdm", "run", "pytest", "-q"]


def _normalize_paths(raw_paths: list[str]) -> list[Path]:
    """Return existing repo-relative Python paths from argv or pre-commit."""

    normalized: list[Path] = []
    for raw_path in raw_paths:
        path = Path(raw_path)
        if not path.is_absolute():
            path = ROOT / path
        if path.suffix != ".py" or not path.exists():
            continue
        normalized.append(path.resolve())
    return normalized


def _staged_python_paths() -> list[Path]:
    """Read staged Python file paths from git when no argv paths are provided."""

    result = subprocess.run(
        [
            "git",
            "diff",
            "--cached",
            "--name-only",
            "--diff-filter=ACMR",
            "--",
            "*.py",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return _normalize_paths([line for line in result.stdout.splitlines() if line.strip()])


def _unit_test_files() -> list[Path]:
    """List all unit test files once for fast inference lookups."""

    return sorted(TESTS_ROOT.rglob("test_*.py")) + sorted(TESTS_ROOT.rglob("*_test.py"))


def _is_unit_test(path: Path) -> bool:
    """Return true when the path points at a unit test module."""

    return path.is_relative_to(TESTS_ROOT)


def _is_source_file(path: Path) -> bool:
    """Return true when the path points at a production source module."""

    return path.is_relative_to(ROOT / "src")


def _infer_tests_for_source(path: Path, all_unit_tests: list[Path]) -> set[Path]:
    """Infer mirrored unit tests for a changed source file."""

    src_relative = path.relative_to(ROOT / "src")
    src_parts = src_relative.parts
    source_stem = path.stem
    mirrored_parts = (
        src_parts[1:-1] if src_parts and src_parts[0] == "skriptoteket" else src_parts[:-1]
    )
    mirrored_dir = TESTS_ROOT.joinpath(*mirrored_parts)

    candidates: set[Path] = set()
    direct_candidates = [
        mirrored_dir / f"test_{source_stem}.py",
        mirrored_dir / f"{source_stem}_test.py",
    ]
    candidates.update(candidate for candidate in direct_candidates if candidate.exists())

    for test_path in all_unit_tests:
        if test_path in candidates:
            continue
        if source_stem in test_path.stem:
            candidates.add(test_path)

    return candidates


def _collect_pytest_targets(paths: list[Path]) -> tuple[list[str], bool]:
    """Map changed paths to pytest targets and whether a unit-suite fallback is needed."""

    if not paths:
        return [], False

    all_unit_tests = _unit_test_files()
    targets: set[Path] = set()
    fallback_to_unit_suite = False

    for path in paths:
        if _is_unit_test(path):
            targets.add(path)
            continue
        if not _is_source_file(path):
            continue
        inferred_tests = _infer_tests_for_source(path, all_unit_tests)
        if inferred_tests:
            targets.update(inferred_tests)
            continue
        fallback_to_unit_suite = True

    sorted_targets = sorted(str(target.relative_to(ROOT)) for target in targets)
    return sorted_targets, fallback_to_unit_suite


def main(argv: list[str]) -> int:
    """Execute the targeted pre-commit pytest gate."""

    candidate_paths = _normalize_paths(argv) if argv else _staged_python_paths()
    pytest_targets, fallback_to_unit_suite = _collect_pytest_targets(candidate_paths)

    if not candidate_paths:
        print("precommit-pytest: no changed Python files; skipping")
        return 0

    if fallback_to_unit_suite:
        print(
            "precommit-pytest: no mirrored unit tests found for at least one source file; running tests/unit"
        )
        command = [*PYTEST_COMMAND, "tests/unit"]
    elif pytest_targets:
        print(f"precommit-pytest: running {' '.join(pytest_targets)}")
        command = [*PYTEST_COMMAND, *pytest_targets]
    else:
        print("precommit-pytest: no unit-test-relevant Python files; skipping")
        return 0

    completed = subprocess.run(command, cwd=ROOT, check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
