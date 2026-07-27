"""Skriptoteket GitHub Actions runtime contract.

Purpose:
    Keep the documentation validation workflow on the approved Node 24 action
    references while preserving its Python input and validation commands.

Relationships:
    - Parses `.github/workflows/docs-validate.yml`, the repository docs gate.
    - Proves the workflow uses action releases with the current Node 24 runtime.
"""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def test_docs_validate_workflow_uses_approved_action_runtimes() -> None:
    workflow = yaml.load(
        (ROOT / ".github/workflows/docs-validate.yml").read_text(encoding="utf-8"),
        Loader=yaml.BaseLoader,
    )
    steps = workflow["jobs"]["docs-validate"]["steps"]

    assert [step["uses"] for step in steps[:2]] == [
        "actions/checkout@v7",
        "actions/setup-python@v7",
    ]
    assert steps[1]["with"] == {"python-version": "3.13"}
    assert [step["run"] for step in steps[2:]] == [
        "python -m pip install --upgrade pip pdm",
        "pdm install --frozen-lockfile -G monorepo-tools",
        "pdm run docs-validate",
    ]
