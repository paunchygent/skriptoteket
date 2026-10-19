"""Run fast staged-file unit tests for pre-commit.

This script keeps the commit-time pytest hook scoped to unit coverage that is
relevant to the changed Python files. It accepts file paths from pre-commit
when available and falls back to staged files from git for direct/manual runs.
When a changed source file has no obvious mirrored unit test, the script falls
back to the whole `tests/unit` suite instead of silently skipping coverage.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS_ROOT = ROOT / "tests" / "unit"
PYTEST_COMMAND = ["pdm", "run", "pytest", "-q"]
EXCLUDED_COMMIT_TIME_MARKERS = frozenset({"docker", "financial", "simulation", "slow"})


@dataclass(frozen=True)
class ExcludedTestTarget:
    """One test module skipped from commit-time execution due to marker policy."""

    path: Path
    markers: tuple[str, ...]


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


def _marker_name_from_expr(node: ast.expr) -> str | None:
    """Extract `pytest.mark.<name>` marker names from simple AST expressions."""

    if isinstance(node, ast.Call):
        return _marker_name_from_expr(node.func)
    if (
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Attribute)
        and isinstance(node.value.value, ast.Name)
        and node.value.value.id == "pytest"
        and node.value.attr == "mark"
    ):
        return node.attr
    return None


def _marker_names_from_expr(node: ast.expr) -> set[str]:
    """Extract marker names from one `pytestmark` assignment expression."""

    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        markers: set[str] = set()
        for element in node.elts:
            markers.update(_marker_names_from_expr(element))
        return markers

    marker_name = _marker_name_from_expr(node)
    return {marker_name} if marker_name else set()


def _excluded_module_markers(path: Path) -> tuple[str, ...]:
    """Return commit-time-excluded module markers declared through `pytestmark`."""

    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return ()

    for statement in tree.body:
        if isinstance(statement, ast.Assign):
            targets = statement.targets
            value = statement.value
        elif isinstance(statement, ast.AnnAssign):
            targets = [statement.target]
            value = statement.value
        else:
            continue

        if value is None:
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == "pytestmark" for target in targets
        ):
            continue

        excluded = sorted(_marker_names_from_expr(value) & EXCLUDED_COMMIT_TIME_MARKERS)
        return tuple(excluded)

    return ()


def _collect_pytest_targets(
    paths: list[Path],
) -> tuple[list[str], bool, list[ExcludedTestTarget]]:
    """Map changed paths to runnable pytest targets, fallback need, and skipped files."""

    if not paths:
        return [], False, []

    all_unit_tests = _unit_test_files()
    targets: set[Path] = set()
    fallback_to_unit_suite = False
    excluded_targets: dict[Path, tuple[str, ...]] = {}

    for path in paths:
        if _is_unit_test(path):
            excluded_markers = _excluded_module_markers(path)
            if excluded_markers:
                excluded_targets[path] = excluded_markers
            else:
                targets.add(path)
            continue
        if not _is_source_file(path):
            continue
        inferred_tests = _infer_tests_for_source(path, all_unit_tests)
        runnable_inferred_tests = {
            inferred_test
            for inferred_test in inferred_tests
            if not _excluded_module_markers(inferred_test)
        }
        for inferred_test in inferred_tests - runnable_inferred_tests:
            excluded_targets[inferred_test] = _excluded_module_markers(inferred_test)
        if runnable_inferred_tests:
            targets.update(runnable_inferred_tests)
            continue
        if inferred_tests:
            continue
        fallback_to_unit_suite = True

    sorted_targets = sorted(str(target.relative_to(ROOT)) for target in targets)
    skipped_targets = [
        ExcludedTestTarget(
            path=path,
            markers=excluded_targets[path],
        )
        for path in sorted(excluded_targets)
    ]
    return sorted_targets, fallback_to_unit_suite, skipped_targets


def main(argv: list[str]) -> int:
    """Execute the targeted pre-commit pytest gate."""

    candidate_paths = _normalize_paths(argv) if argv else _staged_python_paths()
    pytest_targets, fallback_to_unit_suite, excluded_targets = _collect_pytest_targets(
        candidate_paths
    )

    if not candidate_paths:
        print("precommit-pytest: no changed Python files; skipping")
        return 0

    for excluded_target in excluded_targets:
        markers = ", ".join(excluded_target.markers)
        relative_path = excluded_target.path.relative_to(ROOT)
        print(
            f"precommit-pytest: skipping {relative_path} (excluded commit-time markers: {markers})"
        )
        if "simulation" in excluded_target.markers:
            print("precommit-pytest: run `pdm run test-simulations` to validate simulation suites.")

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
