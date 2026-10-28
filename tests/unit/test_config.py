"""Tests for host-vs-container runtime normalization in Settings.

Purpose:
    Protect the local-dev remediation rules that keep host `pdm run dev-local`
    aligned with the documented `/tmp/skriptoteket/...` storage roots and
    container-published Sir Convert ports.

Relationships:
    - Exercises `skriptoteket.config.Settings` without loading the repo `.env`.
    - Covers the PR-0144 host-runtime parity slice only.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from skriptoteket import config
from skriptoteket.config import Settings


def test_host_dev_settings_use_tmp_roots_for_local_storage(monkeypatch) -> None:
    monkeypatch.setattr(config, "_is_running_in_container", lambda: False)

    settings = Settings(
        _env_file=None,
        ENVIRONMENT="development",
        ARTIFACTS_ROOT=Path("/var/lib/skriptoteket/artifacts"),
        VAULT_ROOT=Path("/var/lib/skriptoteket/vault"),
        MEDIA_ROOT=Path("/var/lib/skriptoteket/media"),
    )

    assert settings.ARTIFACTS_ROOT == Path("/tmp/skriptoteket/artifacts")
    assert settings.VAULT_ROOT == Path("/tmp/skriptoteket/vault")
    assert settings.MEDIA_ROOT == Path("/tmp/skriptoteket/media")


def test_host_dev_settings_rewrite_container_only_sir_convert_base_url(monkeypatch) -> None:
    monkeypatch.setattr(config, "_is_running_in_container", lambda: False)

    settings = Settings(
        _env_file=None,
        ENVIRONMENT="development",
        SIR_CONVERT_A_LOT_V2_BASE_URL="http://host.docker.internal:8085",
        SIR_CONVERT_A_LOT_V2_CALLBACK_BASE_URL="http://host.docker.internal:8000",
    )

    assert settings.SIR_CONVERT_A_LOT_V2_BASE_URL == "http://127.0.0.1:8085"
    assert settings.SIR_CONVERT_A_LOT_V2_CALLBACK_BASE_URL == "http://host.docker.internal:8000"


def test_container_runtime_keeps_container_paths_and_urls(monkeypatch) -> None:
    monkeypatch.setattr(config, "_is_running_in_container", lambda: True)

    settings = Settings(
        _env_file=None,
        ENVIRONMENT="development",
        ARTIFACTS_ROOT=Path("/var/lib/skriptoteket/artifacts"),
        VAULT_ROOT=Path("/var/lib/skriptoteket/vault"),
        MEDIA_ROOT=Path("/var/lib/skriptoteket/media"),
        SIR_CONVERT_A_LOT_V2_BASE_URL="http://host.docker.internal:8085",
    )

    assert settings.ARTIFACTS_ROOT == Path("/var/lib/skriptoteket/artifacts")
    assert settings.VAULT_ROOT == Path("/var/lib/skriptoteket/vault")
    assert settings.MEDIA_ROOT == Path("/var/lib/skriptoteket/media")
    assert settings.SIR_CONVERT_A_LOT_V2_BASE_URL == "http://host.docker.internal:8085"


def test_production_defaults_minimize_public_health_details() -> None:
    settings = Settings.model_construct(
        ENVIRONMENT="production",
        HEALTHZ_DETAILED_RESPONSE=None,
        METRICS_IDENTITY_GAUGES_ENABLED=None,
    )

    assert settings.healthz_detailed_response is False
    assert settings.metrics_identity_gauges_enabled is False


def test_non_production_allowed_hosts_include_containerized_dev_backend_alias() -> None:
    settings = Settings.model_construct(
        ENVIRONMENT="development",
        ALLOWED_HOSTS="localhost,127.0.0.1,skriptoteket.hule.education",
    )

    assert settings.allowed_hosts == frozenset(
        {
            "localhost",
            "127.0.0.1",
            "::1",
            "skriptoteket.hule.education",
            "skriptoteket_web",
            "skriptoteket-web",
        }
    )


def test_production_allowed_hosts_do_not_include_test_or_dev_only_aliases() -> None:
    settings = Settings.model_construct(
        ENVIRONMENT="production",
        ALLOWED_HOSTS="localhost,127.0.0.1,::1,skriptoteket.hule.education",
    )

    assert settings.allowed_hosts == frozenset(
        {"localhost", "127.0.0.1", "::1", "skriptoteket.hule.education"}
    )


def test_public_app_base_url_defaults_to_canonical_launch_host() -> None:
    settings = Settings(_env_file=None)

    assert settings.PUBLIC_APP_BASE_URL == "https://skriptoteket.hule.education"


def test_answer_key_completion_requires_the_llm_door_when_enabled() -> None:
    with pytest.raises(ValidationError, match="HULEEDU_INTERNAL_API_KEY"):
        Settings(_env_file=None, LLM_ANSWER_KEY_ENABLED=True, HULEEDU_INTERNAL_API_KEY="")

    with pytest.raises(ValidationError, match="HULEEDU_LLM_PROVIDER_BASE_URL"):
        Settings(
            _env_file=None,
            LLM_ANSWER_KEY_ENABLED=True,
            HULEEDU_LLM_PROVIDER_BASE_URL=" ",
            HULEEDU_INTERNAL_API_KEY="configured-internal-key",
        )


def test_answer_key_completion_accepts_a_configured_llm_door() -> None:
    settings = Settings(
        _env_file=None,
        LLM_ANSWER_KEY_ENABLED=True,
        HULEEDU_INTERNAL_API_KEY="configured-internal-key",
    )

    assert settings.HULEEDU_LLM_PROVIDER_BASE_URL == "http://huleedu_llm_provider_service:8080"


def test_docx_conversion_defaults_to_sixteen_families_per_batch_at_low_effort() -> None:
    settings = Settings(_env_file=None)

    assert settings.LLM_DOCX_BATCH_FAMILIES == 16
    assert settings.LLM_DOCX_CONVERSION_REASONING_EFFORT == "low"


def test_answer_key_model_defaults_to_luna_six_low() -> None:
    settings = Settings(_env_file=None)

    assert settings.LLM_ANSWER_KEY_MODEL == "gpt-6-luna"


@pytest.mark.parametrize("loopback_host", ["localhost", "127.0.0.1", "::1"])
def test_production_refuses_loopback_allowed_hosts(loopback_host: str) -> None:
    with pytest.raises(ValidationError, match=re.escape(loopback_host)):
        Settings(
            _env_file=None,
            ENVIRONMENT="production",
            ALLOWED_HOSTS=f"skriptoteket.hule.education,{loopback_host}",
        )


@pytest.mark.parametrize("environment", ["staging", "development"])
def test_non_production_keeps_loopback_allowed_hosts(environment: str) -> None:
    settings = Settings(_env_file=None, ENVIRONMENT=environment)

    assert {"localhost", "127.0.0.1", "::1"} <= settings.allowed_hosts


def test_production_defaults_and_public_host_drop_loopback_entries() -> None:
    settings = Settings(_env_file=None, ENVIRONMENT="production")

    assert settings.allowed_hosts == frozenset({"skriptoteket.hule.education"})
