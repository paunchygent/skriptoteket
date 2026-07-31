from __future__ import annotations

import importlib.metadata
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SELECTED_VERSION = "0.9.3"
SELECTED_REVISION = "c374461e0a797da27340aaa4a615f52b6045fbe6"
SELECTED_DEPENDENCY = (
    "repository-governance @ "
    "git+https://github.com/paunchygent/skill-repository.git"
    f"@{SELECTED_REVISION}#subdirectory=packages/repository_governance"
)
ROUTINE_BINDINGS = {
    "setup",
    "new-worktree",
    "format",
    "lint",
    "typecheck",
    "test",
    "check",
    "new-doc",
    "new-epic",
    "new-story",
    "new-task",
    "new-review",
    "docs-sync",
    "docs-validate",
    "format-md",
    "check-md",
    "format-md-all",
    "check-md-all",
}
AUXILIARY_BINDINGS = {"run-hemma", "staleness-audit"}


def test_selected_package_identity_is_exact() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    lock = tomllib.loads((ROOT / "pdm.lock").read_text(encoding="utf-8"))

    assert SELECTED_DEPENDENCY in project["dependency-groups"]["monorepo-tools"]
    package = next(item for item in lock["package"] if item["name"] == "repository-governance")
    assert package["version"] == SELECTED_VERSION
    assert package["ref"] == SELECTED_REVISION
    assert package["revision"] == SELECTED_REVISION
    assert importlib.metadata.version("repository-governance") == SELECTED_VERSION


def test_minimal_setup_facts_and_generated_bindings_are_complete() -> None:
    project_path = ROOT / "pyproject.toml"
    project_text = project_path.read_text(encoding="utf-8")
    project = tomllib.loads(project_text)

    facts = project["tool"]["repository-governance"]
    assert facts["schema-version"] == 3
    assert facts["repository"] == "skriptoteket"
    assert facts["owners"] == {"service": ["skriptoteket"]}
    assert facts["setup"] == {"projects": [{"path": ".", "groups": ["default", "monorepo-tools"]}]}
    scripts = project["tool"]["pdm"]["scripts"]
    assert ROUTINE_BINDINGS <= scripts.keys()
    assert AUXILIARY_BINDINGS <= scripts.keys()
    assert project_text.count("# repository-governance:bindings:start") == 1
    assert project_text.count("# repository-governance:bindings:end") == 1
    assert project_text.count("# repository-governance:auxiliary-bindings:start") == 1
    assert project_text.count("# repository-governance:auxiliary-bindings:end") == 1
