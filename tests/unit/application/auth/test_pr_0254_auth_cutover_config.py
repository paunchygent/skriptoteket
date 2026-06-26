"""Unit tests for PR-0254 auth-cutover command configuration.

Purpose:
    Prove the PR-0254 one-command smoke resolves the dedicated lifecycle proof
    account before falling back to generic bootstrap credentials.

Relationships:
    - Exercises `scripts.playwright_pr_0254_auth_cutover` credential selection.
    - Complements manifest-contract tests by keeping the live smoke's
      contributor credential lane durable.
"""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import pytest

from scripts.playwright_pr_0254_auth_cutover import (
    DEFAULT_HULEEDU_TASK_0326_ARTIFACT,
    _credentials,
    _resolve_artifacts,
)


def test_credentials_prefer_lifecycle_proof_dotenv_over_bootstrap(
    monkeypatch,
) -> None:
    monkeypatch.delenv("PLAYWRIGHT_EMAIL", raising=False)
    monkeypatch.delenv("PLAYWRIGHT_PASSWORD", raising=False)
    dotenv = {
        "SKRIPTOTEKET_LIFECYCLE_PROOF_EMAIL": "proof@example.test",
        "SKRIPTOTEKET_LIFECYCLE_PROOF_PASSWORD": "proof-password",
        "BOOTSTRAP_SUPERUSER_EMAIL": "bootstrap@example.test",
        "BOOTSTRAP_SUPERUSER_PASSWORD": "bootstrap-password",
    }

    email, password = _credentials(email=None, password=None, dotenv=dotenv)

    assert email == "proof@example.test"
    assert password == "proof-password"


def test_credentials_prefer_playwright_env_over_lifecycle_proof(
    monkeypatch,
) -> None:
    monkeypatch.setenv("PLAYWRIGHT_EMAIL", "env@example.test")
    monkeypatch.setenv("PLAYWRIGHT_PASSWORD", "env-password")
    dotenv = {
        "SKRIPTOTEKET_LIFECYCLE_PROOF_EMAIL": "proof@example.test",
        "SKRIPTOTEKET_LIFECYCLE_PROOF_PASSWORD": "proof-password",
    }

    email, password = _credentials(email=None, password=None, dotenv=dotenv)

    assert email == "env@example.test"
    assert password == "env-password"


def test_credentials_cli_overrides_everything(monkeypatch) -> None:
    monkeypatch.setenv("PLAYWRIGHT_EMAIL", "env@example.test")
    monkeypatch.setenv("PLAYWRIGHT_PASSWORD", "env-password")
    dotenv = {
        "SKRIPTOTEKET_LIFECYCLE_PROOF_EMAIL": "proof@example.test",
        "SKRIPTOTEKET_LIFECYCLE_PROOF_PASSWORD": "proof-password",
    }

    email, password = _credentials(
        email="cli@example.test",
        password="cli-password",
        dotenv=dotenv,
    )

    assert email == "cli@example.test"
    assert password == "cli-password"


def test_default_huleedu_subject_export_uses_current_shared_lane() -> None:
    assert DEFAULT_HULEEDU_TASK_0326_ARTIFACT.endswith(
        "skriptoteket-auth-bootstrap/local-shared-verify-export.json"
    )


def test_unsupported_huleedu_subject_export_name_is_rejected(monkeypatch) -> None:
    monkeypatch.delenv("HULEEDU_TASK_0326_ARTIFACT", raising=False)
    args = Namespace(
        huleedu_task_0326_artifact=("../../huleedu/.artifacts/unsupported-subject-export.json"),
        huleedu_task_0327_artifact="task-0327.json",
        pr_0261_artifact="pr-0261.json",
        pr_0262_artifact="pr-0262.json",
    )

    with pytest.raises(SystemExit, match="local-shared-verify-export.json"):
        _resolve_artifacts(args)


def test_current_shared_export_default_resolves_when_no_override(monkeypatch) -> None:
    monkeypatch.delenv("HULEEDU_TASK_0326_ARTIFACT", raising=False)
    args = Namespace(
        huleedu_task_0326_artifact=None,
        huleedu_task_0327_artifact="task-0327.json",
        pr_0261_artifact="pr-0261.json",
        pr_0262_artifact="pr-0262.json",
    )

    artifacts = _resolve_artifacts(args)

    assert artifacts.huleedu_task_0326 == Path(DEFAULT_HULEEDU_TASK_0326_ARTIFACT)
