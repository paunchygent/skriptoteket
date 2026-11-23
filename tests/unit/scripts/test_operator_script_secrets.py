"""Operator-script secret routing tests (TASK-SKRIPT-REP-0074).

Domain purpose:
    Prove every operator command that reads BOOTSTRAP_SUPERUSER_PASSWORD,
    HULEEDU_INTERNAL_API_KEY, SIR_CONVERT_A_LOT_V2_API_KEY, PLAYWRIGHT_PASSWORD
    or SKRIPTOTEKET_LIFECYCLE_PROOF_PASSWORD runs through
    `agent-secrets run --set skriptoteket-operator` via its pdm script, and that
    the changed credential helpers never fall back to .env for a password.

Relationships:
    - Guards the EPIC-SKILL-18 leaf: secrets reach processes through
      agent-secrets; .env keeps only non-secret configuration.
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]

AGENT_SECRETS_PREFIX = "agent-secrets run --set skriptoteket-operator -- "
PROD_AGENT_SECRETS_PREFIX = "agent-secrets run --set skriptoteket-prod -- "

WRAPPED_PDM_SCRIPTS = {
    "pr-0254-auth-cutover": "python -m scripts.playwright_pr_0254_auth_cutover",
    "auth-cutover-proof": "python -m scripts.playwright_pr_0254_auth_cutover",
    "playwright-profile-verify": "python -m scripts.playwright_profile_verify",
    "ai-prompt-eval": "python -m scripts.ai_prompt_eval.run_live_backend",
    "exam-conversion-eval": "python -m scripts.exam_conversion_eval",
    "labeling-feasibility": "python -m scripts.labeling_feasibility",
    "item-type-labeler-live": "python -m scripts.item_type_labeler_live",
    "textbook-corpus-baseline": "python -m scripts.build_textbook_corpus_baseline",
    "transcript-parity-proof": "python -m scripts.transcript_parity_proof_launcher",
    "audio-transcription-reattempt-proof": (
        "python -m scripts.audio_transcription_retryable_reattempt_public_proof"
    ),
    "auth-edge-bootstrap-preflight": "python -m skriptoteket.cli auth-edge-bootstrap-preflight",
    "seed-script-bank": "python -m skriptoteket.cli seed-script-bank",
}

# Production operator scripts inject the skriptoteket-prod set and run the
# seed inside the web container via `docker compose exec`, preserving the
# injected variable names through sudo (agent-secrets runs on Hemma, not in
# the web image).
PROD_WRAPPED_PDM_SCRIPTS = {
    "hemma-seed-script-bank": (
        'bash -c \'sudo --preserve-env="$AGENT_SECRETS_VARIABLES" docker compose '
        "-f compose.prod.yaml exec -e PYTHONPATH=/app/src -e BOOTSTRAP_SUPERUSER_EMAIL "
        "-e BOOTSTRAP_SUPERUSER_PASSWORD web pdm run python -m skriptoteket.cli "
        'seed-script-bank "$@"\' bash'
    ),
}

SECRET_ENV_VARS = (
    "BOOTSTRAP_SUPERUSER_PASSWORD",
    "HULEEDU_INTERNAL_API_KEY",
    "SIR_CONVERT_A_LOT_V2_API_KEY",
    "PLAYWRIGHT_PASSWORD",
    "SKRIPTOTEKET_LIFECYCLE_PROOF_PASSWORD",
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
    for name, inner_command in PROD_WRAPPED_PDM_SCRIPTS.items():
        expected = [f"{PROD_AGENT_SECRETS_PREFIX}{inner_command}"]
        assert _script_commands(scripts[name]) == expected, name

    wrapped = {
        name
        for name, entry in scripts.items()
        if any("agent-secrets" in command for command in _script_commands(entry))
    }
    assert wrapped == set(WRAPPED_PDM_SCRIPTS) | set(PROD_WRAPPED_PDM_SCRIPTS)


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
            "BOOTSTRAP_SUPERUSER_PASSWORD=dotenv-secret\n"
            "PLAYWRIGHT_PASSWORD=dotenv-secret\n"
            "SKRIPTOTEKET_LIFECYCLE_PROOF_PASSWORD=dotenv-secret\n",
            encoding="utf-8",
        )
        for key in (
            "BASE_URL",
            "BOOTSTRAP_SUPERUSER_EMAIL",
            "BOOTSTRAP_SUPERUSER_PASSWORD",
            "PLAYWRIGHT_PASSWORD",
            "SKRIPTOTEKET_LIFECYCLE_PROOF_PASSWORD",
        ):
            os.environ.pop(key, None)

        playwright_profile_verify._load_dotenv_config(dotenv_path)

        assert os.environ["BASE_URL"] == "http://example.test"
        assert os.environ["BOOTSTRAP_SUPERUSER_EMAIL"] == "dev@example.test"
        assert os.environ.get("BOOTSTRAP_SUPERUSER_PASSWORD") is None
        assert os.environ.get("PLAYWRIGHT_PASSWORD") is None
        assert os.environ.get("SKRIPTOTEKET_LIFECYCLE_PROOF_PASSWORD") is None
    finally:
        os.environ.clear()
        os.environ.update(snapshot)


def test_playwright_config_never_reads_playwright_password_from_dotenv(monkeypatch) -> None:
    from scripts._playwright_config import _get_credentials

    for key in (
        "PLAYWRIGHT_EMAIL",
        "PLAYWRIGHT_PASSWORD",
        "BOOTSTRAP_SUPERUSER_EMAIL",
        "BOOTSTRAP_SUPERUSER_PASSWORD",
    ):
        monkeypatch.delenv(key, raising=False)
    dotenv = {
        "PLAYWRIGHT_EMAIL": "smoke@example.test",
        "PLAYWRIGHT_PASSWORD": "dotenv-secret",
    }

    email, password = _get_credentials(dotenv=dotenv)

    assert email == "smoke@example.test"
    assert password is None


def test_playwright_config_reads_playwright_password_from_env(monkeypatch) -> None:
    from scripts._playwright_config import _get_credentials

    monkeypatch.setenv("PLAYWRIGHT_PASSWORD", "env-secret")
    dotenv = {"PLAYWRIGHT_PASSWORD": "dotenv-secret"}

    _, password = _get_credentials(dotenv=dotenv)

    assert password == "env-secret"


def test_pr_0254_credentials_never_read_secret_passwords_from_dotenv(monkeypatch) -> None:
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
        "PLAYWRIGHT_EMAIL": "smoke@example.test",
        "PLAYWRIGHT_PASSWORD": "dotenv-secret",
        "SKRIPTOTEKET_LIFECYCLE_PROOF_EMAIL": "proof@example.test",
        "SKRIPTOTEKET_LIFECYCLE_PROOF_PASSWORD": "dotenv-secret",
    }

    email, password = _credentials(email=None, password=None, dotenv=dotenv)

    assert email == "smoke@example.test"
    assert password is None


def test_pr_0254_credentials_read_bootstrap_password_from_env(monkeypatch) -> None:
    from scripts.playwright_pr_0254_auth_cutover import _credentials

    for key in ("PLAYWRIGHT_EMAIL", "PLAYWRIGHT_PASSWORD"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("BOOTSTRAP_SUPERUSER_PASSWORD", "env-secret")
    dotenv = {"BOOTSTRAP_SUPERUSER_PASSWORD": "dotenv-secret"}

    _, password = _credentials(email=None, password=None, dotenv=dotenv)

    assert password == "env-secret"


def test_ai_prompt_eval_never_reads_playwright_password_from_dotenv(monkeypatch) -> None:
    from scripts.ai_prompt_eval.cli import _get_credentials

    for key in (
        "PLAYWRIGHT_EMAIL",
        "PLAYWRIGHT_PASSWORD",
        "BOOTSTRAP_SUPERUSER_EMAIL",
        "BOOTSTRAP_SUPERUSER_PASSWORD",
    ):
        monkeypatch.delenv(key, raising=False)
    dotenv = {
        "PLAYWRIGHT_EMAIL": "smoke@example.test",
        "PLAYWRIGHT_PASSWORD": "dotenv-secret",
    }

    email, password = _get_credentials(dotenv=dotenv)

    assert email == "smoke@example.test"
    assert password is None


def test_task_0376_config_never_reads_playwright_password_from_dotenv(
    monkeypatch, tmp_path: Path
) -> None:
    from scripts._playwright_task_0376_config import parse_args

    for key in ("PLAYWRIGHT_EMAIL", "PLAYWRIGHT_PASSWORD", "DOTENV_PATH"):
        monkeypatch.delenv(key, raising=False)
    dotenv_path = tmp_path / ".env.prod-smoke"
    dotenv_path.write_text(
        "PLAYWRIGHT_EMAIL=smoke@example.test\nPLAYWRIGHT_PASSWORD=dotenv-secret\n",
        encoding="utf-8",
    )

    with pytest.raises(SystemExit):
        parse_args(["--dotenv", str(dotenv_path)])


def test_task_0376_config_reads_playwright_password_from_env(monkeypatch, tmp_path: Path) -> None:
    from scripts._playwright_task_0376_config import parse_args

    monkeypatch.delenv("PLAYWRIGHT_EMAIL", raising=False)
    monkeypatch.setenv("PLAYWRIGHT_PASSWORD", "env-secret")
    dotenv_path = tmp_path / ".env.prod-smoke"
    dotenv_path.write_text(
        "PLAYWRIGHT_EMAIL=smoke@example.test\nPLAYWRIGHT_PASSWORD=dotenv-secret\n",
        encoding="utf-8",
    )

    config = parse_args(["--dotenv", str(dotenv_path)])

    assert config.email == "smoke@example.test"
    assert config.password == "env-secret"
