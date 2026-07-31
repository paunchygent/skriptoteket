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

ROOT = Path(__file__).resolve().parents[1]
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


def test_minimal_setup_facts_and_generated_bindings_are_complete() -> None:
    project_path = ROOT / "pyproject.toml"
    project_text = project_path.read_text(encoding="utf-8")
    project = tomllib.loads(project_text)

    facts = project["tool"]["repository-governance"]
    assert facts == {
        "schema-version": 3,
        "repository": "skriptoteket",
        "owners": {"service": ["skriptoteket"]},
        "setup": {"projects": [{"path": ".", "groups": ["default", "monorepo-tools"]}]},
    }
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
