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
