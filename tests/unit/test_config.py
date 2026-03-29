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

from pathlib import Path

from skriptoteket import config
from skriptoteket.config import Settings


def test_host_dev_settings_use_tmp_roots_for_local_storage(monkeypatch) -> None:
    monkeypatch.setattr(config, "_is_running_in_container", lambda: False)

    settings = Settings(
        _env_file=None,
        ENVIRONMENT="development",
        ARTIFACTS_ROOT=Path("/var/lib/skriptoteket/artifacts"),
        VAULT_ROOT=Path("/var/lib/skriptoteket/vault"),
    )

    assert settings.ARTIFACTS_ROOT == Path("/tmp/skriptoteket/artifacts")
    assert settings.VAULT_ROOT == Path("/tmp/skriptoteket/vault")


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
        SIR_CONVERT_A_LOT_V2_BASE_URL="http://host.docker.internal:8085",
    )

    assert settings.ARTIFACTS_ROOT == Path("/var/lib/skriptoteket/artifacts")
    assert settings.VAULT_ROOT == Path("/var/lib/skriptoteket/vault")
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
        {"localhost", "127.0.0.1", "skriptoteket.hule.education", "skriptoteket_web"}
    )


def test_production_allowed_hosts_do_not_include_test_or_dev_only_aliases() -> None:
    settings = Settings.model_construct(
        ENVIRONMENT="production",
        ALLOWED_HOSTS="localhost,127.0.0.1,::1,skriptoteket.hule.education",
    )

    assert settings.allowed_hosts == frozenset(
        {"localhost", "127.0.0.1", "::1", "skriptoteket.hule.education"}
    )


def test_trusted_proxy_cidrs_parse_as_unique_csv_values() -> None:
    settings = Settings.model_construct(TRUSTED_PROXY_CIDRS="127.0.0.1/32, 10.0.0.0/8,127.0.0.1/32")

    assert settings.trusted_proxy_cidrs == frozenset({"127.0.0.1/32", "10.0.0.0/8"})
