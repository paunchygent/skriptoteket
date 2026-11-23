"""Operator-script secret routing tests (TASK-SKRIPT-REP-0074).

Domain purpose:
    Prove every operator command that reads BOOTSTRAP_SUPERUSER_PASSWORD,
    HULEEDU_INTERNAL_API_KEY or SIR_CONVERT_A_LOT_V2_API_KEY runs through
    `agent-secrets run --set skriptoteket-operator` via its pdm script, and that
    the changed credential helpers never fall back to .env for the password.

Relationships:
    - Guards the EPIC-SKILL-18 leaf: secrets reach processes through
      agent-secrets; .env keeps only non-secret configuration.
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

AGENT_SECRETS_PREFIX = "agent-secrets run --set skriptoteket-operator -- "

WRAPPED_PDM_SCRIPTS = {
    "pr-0254-auth-cutover": "python -m scripts.playwright_pr_0254_auth_cutover",
    "auth-cutover-proof": "python -m scripts.playwright_pr_0254_auth_cutover",
    "playwright-profile-verify": "python -m scripts.playwright_profile_verify",
    "ai-prompt-eval": "python -m scripts.ai_prompt_eval.run_live_backend",
    "exam-conversion-eval": "python -m scripts.exam_conversion_eval",
    "labeling-feasibility": "python -m scripts.labeling_feasibility",
    "item-type-labeler-live": "python -m scripts.item_type_labeler_live",
    "textbook-corpus-baseline": "python -m scripts.build_textbook_corpus_baseline",
    "auth-edge-bootstrap-preflight": "python -m skriptoteket.cli auth-edge-bootstrap-preflight",
    "seed-script-bank": "python -m skriptoteket.cli seed-script-bank",
}

SECRET_ENV_VARS = (
    "BOOTSTRAP_SUPERUSER_PASSWORD",
    "HULEEDU_INTERNAL_API_KEY",
    "SIR_CONVERT_A_LOT_V2_API_KEY",
)


def _script_commands(entry: object) -> list[str]:
    if isinstance(entry, str):
        return [entry]
    if isinstance(entry, dict):
        if "cmd" in entry:
            return [str(entry["cmd"])]
        if "composite" in entry:
            return [str(step) for step in entry["composite"]]
    return []


def test_secret_reading_operator_scripts_run_through_agent_secrets() -> None:
    scripts = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["pdm"][
        "scripts"
    ]

    for name, inner_command in WRAPPED_PDM_SCRIPTS.items():
        assert _script_commands(scripts[name]) == [f"{AGENT_SECRETS_PREFIX}{inner_command}"], name

    wrapped = {
        name
        for name, entry in scripts.items()
        if any("agent-secrets" in command for command in _script_commands(entry))
    }
    assert wrapped == set(WRAPPED_PDM_SCRIPTS)


def test_pdm_script_env_overrides_survive_wrapping() -> None:
    scripts = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["pdm"][
        "scripts"
    ]
    src_pythonpath_scripts = (
        "ai-prompt-eval",
        "exam-conversion-eval",
        "labeling-feasibility",
        "item-type-labeler-live",
        "auth-edge-bootstrap-preflight",
        "seed-script-bank",
    )

    for name in src_pythonpath_scripts:
        entry = scripts[name]
        assert isinstance(entry, dict), name
        assert entry["env"] == {"PYTHONPATH": "src"}, name


def test_playwright_config_never_reads_bootstrap_password_from_dotenv(monkeypatch) -> None:
    from scripts._playwright_config import _get_credentials

    for key in (
        "PLAYWRIGHT_EMAIL",
        "PLAYWRIGHT_PASSWORD",
        "BOOTSTRAP_SUPERUSER_EMAIL",
        "BOOTSTRAP_SUPERUSER_PASSWORD",
    ):
        monkeypatch.delenv(key, raising=False)
    dotenv = {
        "BOOTSTRAP_SUPERUSER_EMAIL": "dev@example.test",
        "BOOTSTRAP_SUPERUSER_PASSWORD": "dotenv-secret",
    }

    email, password = _get_credentials(dotenv=dotenv)

    assert email == "dev@example.test"
    assert password is None


def test_playwright_config_reads_bootstrap_password_from_env(monkeypatch) -> None:
    from scripts._playwright_config import _get_credentials

    for key in ("PLAYWRIGHT_EMAIL", "PLAYWRIGHT_PASSWORD"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("BOOTSTRAP_SUPERUSER_PASSWORD", "env-secret")
    dotenv = {"BOOTSTRAP_SUPERUSER_PASSWORD": "dotenv-secret"}

    _, password = _get_credentials(dotenv=dotenv)

    assert password == "env-secret"


def test_pr_0254_credentials_never_read_bootstrap_password_from_dotenv(monkeypatch) -> None:
    from scripts.playwright_pr_0254_auth_cutover import _credentials

    for key in (
        "PLAYWRIGHT_EMAIL",
        "PLAYWRIGHT_PASSWORD",
        "SKRIPTOTEKET_LIFECYCLE_PROOF_EMAIL",
        "SKRIPTOTEKET_LIFECYCLE_PROOF_PASSWORD",
        "BOOTSTRAP_SUPERUSER_EMAIL",
        "BOOTSTRAP_SUPERUSER_PASSWORD",
    ):
        monkeypatch.delenv(key, raising=False)
    dotenv = {
        "BOOTSTRAP_SUPERUSER_EMAIL": "dev@example.test",
        "BOOTSTRAP_SUPERUSER_PASSWORD": "dotenv-secret",
    }

    email, password = _credentials(email=None, password=None, dotenv=dotenv)

    assert email == "dev@example.test"
    assert password is None


def test_ai_prompt_eval_credentials_never_read_bootstrap_password_from_dotenv(
    monkeypatch,
) -> None:
    from scripts.ai_prompt_eval.cli import _get_credentials

    for key in (
        "PLAYWRIGHT_EMAIL",
        "PLAYWRIGHT_PASSWORD",
        "BOOTSTRAP_SUPERUSER_EMAIL",
        "BOOTSTRAP_SUPERUSER_PASSWORD",
    ):
        monkeypatch.delenv(key, raising=False)
    dotenv = {
        "BOOTSTRAP_SUPERUSER_EMAIL": "dev@example.test",
        "BOOTSTRAP_SUPERUSER_PASSWORD": "dotenv-secret",
    }

    email, password = _get_credentials(dotenv=dotenv)

    assert email == "dev@example.test"
    assert password is None


def test_profile_verify_dotenv_load_keeps_config_but_not_the_password(
    tmp_path: Path,
) -> None:
    snapshot = os.environ.copy()
    try:
        from scripts import playwright_profile_verify

        dotenv_path = tmp_path / ".env"
        dotenv_path.write_text(
            "BASE_URL=http://example.test\n"
            "BOOTSTRAP_SUPERUSER_EMAIL=dev@example.test\n"
            "BOOTSTRAP_SUPERUSER_PASSWORD=dotenv-secret\n",
            encoding="utf-8",
        )
        for key in ("BASE_URL", "BOOTSTRAP_SUPERUSER_EMAIL", "BOOTSTRAP_SUPERUSER_PASSWORD"):
            os.environ.pop(key, None)

        playwright_profile_verify._load_dotenv_config(dotenv_path)

        assert os.environ["BASE_URL"] == "http://example.test"
        assert os.environ["BOOTSTRAP_SUPERUSER_EMAIL"] == "dev@example.test"
        assert os.environ.get("BOOTSTRAP_SUPERUSER_PASSWORD") is None
    finally:
        os.environ.clear()
        os.environ.update(snapshot)
