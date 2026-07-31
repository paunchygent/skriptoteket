from __future__ import annotations

import importlib.metadata
import re
import tomllib
from pathlib import Path

from repository_governance.routine.bindings import (
    AUXILIARY_BINDINGS,
    ROUTINE_BINDINGS,
    validate_reserved_bindings,
)

ROOT = Path(__file__).resolve().parents[3]
DEPENDENCY_PATTERN = re.compile(
    r"repository-governance @ "
    r"git\+https://github\.com/paunchygent/skill-repository\.git"
    r"@(?P<revision>[0-9a-f]{40})"
    r"#subdirectory=packages/repository_governance"
)


def test_selected_package_identity_is_exact() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    lock = tomllib.loads((ROOT / "pdm.lock").read_text(encoding="utf-8"))

    dependencies = [
        dependency
        for dependency in project["dependency-groups"]["monorepo-tools"]
        if dependency.startswith("repository-governance @ ")
    ]
    assert len(dependencies) == 1
    match = DEPENDENCY_PATTERN.fullmatch(dependencies[0])
    assert match is not None
    selected_revision = match.group("revision")

    package = next(item for item in lock["package"] if item["name"] == "repository-governance")
    assert package["git"] == "https://github.com/paunchygent/skill-repository.git"
    assert package["subdirectory"] == "packages/repository_governance"
    assert package["ref"] == selected_revision
    assert package["revision"] == selected_revision
    assert importlib.metadata.version("repository-governance") == package["version"]


def test_repository_facts_and_generated_bindings_are_complete() -> None:
    project_path = ROOT / "pyproject.toml"
    project_text = project_path.read_text(encoding="utf-8")
    project = tomllib.loads(project_text)

    facts = project["tool"]["repository-governance"]
    assert facts["schema-version"] == 3
    assert facts["repository"] == "skriptoteket"
    assert facts["owners"] == {"service": ["skriptoteket"]}
    assert facts["hemma"] == {
        "host": "hemma",
        "repository-root": "/home/paunchygent/apps/skriptoteket",
        "forward-environment": [],
    }
    assert facts["setup"] == {
        "projects": [{"path": ".", "groups": ["default", "monorepo-tools", "dev"]}],
    }
    assert facts["frontend"] == {
        "workspace-yaml": "frontend/pnpm-workspace.yaml",
        "package-manager-manifest": "frontend/package.json",
        "dependency-manifests": [
            "frontend/package.json",
            "frontend/apps/skriptoteket/package.json",
        ],
        "resource-manifest": (
            "frontend/apps/skriptoteket/src/design-system/huleedu-integrated/manifest.json"
        ),
        "resource-package": (
            "frontend/apps/skriptoteket/src/design-system/huleedu-integrated/package.json"
        ),
        "justified-exceptions": [],
    }
    quality = facts["quality"]
    assert quality["cohorts"] == [
        {
            "name": "backend-source",
            "kind": "path",
            "path": "src",
            "typecheck": "backend-typecheck",
        },
        {
            "name": "unit-domain",
            "kind": "component-root",
            "root": "tests/unit",
            "test-target": "component",
            "typecheck": "backend-typecheck",
            "test": "backend-test",
        },
        {
            "name": "integration",
            "kind": "path",
            "path": "tests/integration",
            "typecheck": "backend-typecheck",
            "test": "backend-test",
        },
        {
            "name": "frontend",
            "kind": "path",
            "path": "frontend",
            "typecheck": "frontend-typecheck",
            "test": "frontend-test",
        },
    ]
    assert [row["name"] for row in quality["producers"]] == [
        "backend-typecheck",
        "backend-test",
        "frontend-typecheck",
        "frontend-test",
    ]
    assert [row["name"] for row in quality["validators"]] == [
        "docs-validate",
        "skills-validate",
        "handoff-validate",
        "bindings",
    ]
    scripts = project["tool"]["pdm"]["scripts"]
    assert validate_reserved_bindings(project_path) == ()
    for name, command in {**ROUTINE_BINDINGS, **AUXILIARY_BINDINGS}.items():
        assert scripts[name] == command

    assert scripts["dev"] == (
        "uvicorn --app-dir src skriptoteket.web.app:app --reload --host 127.0.0.1 --port 8000"
    )
    assert scripts["fe-build"] == {
        "cmd": "pnpm --filter @skriptoteket/spa build",
        "working_dir": "frontend",
    }
    assert scripts["test-parallel"] == "python -m scripts.run_pytest_with_native_libs -n auto"
    assert scripts["hemma-deploy"] == "bash ./scripts/hemma_deploy_start.sh"
    assert scripts["dev-stack"] == "python -m scripts.dev_stack"
