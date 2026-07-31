"""Proof that the legacy validator is historical-only and outside current gates."""

from __future__ import annotations

from pathlib import Path

from scripts.historical_docs.reviews import validate_review_targets
from scripts.historical_docs.validate_historical_docs import historical_docs, load_contract


def test_historical_selector_excludes_current_shared_contract_records() -> None:
    paths = [
        Path("docs/backlog/prs/pr-0410-st-21-11-correction-replay-artifact-set-consumer.md"),
        Path("docs/backlog/tasks/task-skript-rep-0003-migrate-current-governed-corpus.md"),
    ]

    assert historical_docs(paths, load_contract()) == [paths[0]]


def test_current_gates_use_only_shared_validation() -> None:
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
    hooks = Path(".pre-commit-config.yaml").read_text(encoding="utf-8")

    assert 'docs-validate = "repository-governance-docs-validate"' in pyproject
    assert "scripts.historical_docs" not in pyproject
    assert "entry: pdm run docs-validate" in hooks
    assert "scripts.historical_docs" not in hooks


def test_historical_review_does_not_require_migrated_parent_to_remain_legacy() -> None:
    path = Path("docs/backlog/reviews/review-epic-21-example.md")
    known_docs = {
        path.as_posix(): (
            path,
            {
                "type": "review",
                "id": "REV-EPIC-21",
                "epic": "EPIC-21",
                "stories": [],
                "prs": [],
                "adrs": [],
            },
        )
    }

    assert validate_review_targets([path], known_docs) == []
