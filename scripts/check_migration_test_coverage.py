"""Enforce explicit integration coverage for every Alembic revision.

This script compares the revisions declared under ``migrations/versions`` with
the dedicated migration tests and the uncovered-revision registry used by the
parameterized migration coverage suite. It fails fast when a migration lands
without matching integration coverage.
"""

from __future__ import annotations

import ast
from pathlib import Path

from tests.integration.migration_schema_assertions import COVERED_REVISION_IDS


def _parse_revision_id(path: Path) -> str:
    module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in module.body:
        if isinstance(node, ast.Assign):
            targets = [target.id for target in node.targets if isinstance(target, ast.Name)]
            if "revision" in targets and isinstance(node.value, ast.Constant):
                return str(node.value.value)
        if isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == "revision":
                if isinstance(node.value, ast.Constant):
                    return str(node.value.value)
    raise ValueError(f"Could not find Alembic revision id in {path}")


def _migration_revisions() -> set[str]:
    revisions = set()
    for path in Path("migrations/versions").glob("*.py"):
        if path.name == "__init__.py":
            continue
        revisions.add(_parse_revision_id(path))
    return revisions


def _dedicated_test_revisions() -> set[str]:
    revisions = set()
    for path in Path("tests/integration").glob("test_migration_*_idempotent.py"):
        if path.name == "test_migration_revision_coverage_idempotent.py":
            continue
        revision_id = path.stem.removeprefix("test_migration_").removesuffix("_idempotent")
        revisions.add(revision_id)
    return revisions


def main() -> int:
    """Validate that every migration revision has explicit integration coverage."""
    migration_revisions = _migration_revisions()
    covered_revisions = _dedicated_test_revisions() | set(COVERED_REVISION_IDS)

    missing = sorted(migration_revisions - covered_revisions)
    extra = sorted(covered_revisions - migration_revisions)

    if missing:
        raise SystemExit(
            "Missing migration integration coverage for revisions:\n- " + "\n- ".join(missing)
        )
    if extra:
        raise SystemExit(
            "Coverage registry references unknown migration revisions:\n- " + "\n- ".join(extra)
        )

    print(f"migration-test-coverage: ok ({len(migration_revisions)} revisions covered)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
