"""Compose secrets overlays hold every secret interpolation behind agent-secrets guards.

Purpose:
    TASK-SKRIPT-REP-0072 (EPIC-SKILL-18): the base compose files interpolate no
    secret. Each project has one secrets overlay that carries every secret
    environment entry as ``${VAR:?run through agent-secrets run --set <set>}``,
    so only the up/build/run paths that pass the overlay through
    ``agent-secrets run`` resolve secrets.

Relationships:
    - Guards ``compose.prod.yaml``, ``compose.hemma-dev.yaml`` and
      ``compose.observability.yaml`` against reintroduced secret
      interpolations.
    - Guards ``compose.secrets.prod.yaml``, ``compose.secrets.hemma-dev.yaml``
      and ``compose.secrets.observability.yaml`` for the required guarded
      entries and set names.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]

PROD_SET = "skriptoteket-prod"
STAGING_SET = "skriptoteket-staging"

# (base file, overlay file, agent-secrets set, {service: {env name: secret variable}})
COMPOSE_SECRET_SPLIT: tuple[tuple[str, str, str, dict[str, dict[str, str]]], ...] = (
    (
        "compose.prod.yaml",
        "compose.secrets.prod.yaml",
        PROD_SET,
        {
            "web": {
                "DATABASE_URL": "SKRIPTOTEKET_DB_PASSWORD",
                "SECRET_KEY": "SECRET_KEY",
                "EMAIL_SMTP_PASSWORD": "EMAIL_SMTP_PASSWORD",
                "HULEEDU_INTERNAL_API_KEY": "HULEEDU_INTERNAL_API_KEY",
                "SIR_CONVERT_A_LOT_V2_API_KEY": "SIR_CONVERT_A_LOT_V2_API_KEY",
            },
            "worker": {
                "DATABASE_URL": "SKRIPTOTEKET_DB_PASSWORD",
                "HULEEDU_INTERNAL_API_KEY": "HULEEDU_INTERNAL_API_KEY",
                "SIR_CONVERT_A_LOT_V2_API_KEY": "SIR_CONVERT_A_LOT_V2_API_KEY",
            },
        },
    ),
    (
        "compose.hemma-dev.yaml",
        "compose.secrets.hemma-dev.yaml",
        STAGING_SET,
        {
            "db": {"POSTGRES_PASSWORD": "SKRIPTOTEKET_DEV_DB_PASSWORD"},
            "web": {
                "DATABASE_URL": "SKRIPTOTEKET_DEV_DB_PASSWORD",
                "HULEEDU_INTERNAL_API_KEY": "HULEEDU_INTERNAL_API_KEY",
            },
            "worker": {
                "DATABASE_URL": "SKRIPTOTEKET_DEV_DB_PASSWORD",
                "HULEEDU_INTERNAL_API_KEY": "HULEEDU_INTERNAL_API_KEY",
            },
        },
    ),
    (
        "compose.observability.yaml",
        "compose.secrets.observability.yaml",
        PROD_SET,
        {"grafana": {"GF_SECURITY_ADMIN_PASSWORD": "GRAFANA_ADMIN_PASSWORD"}},
    ),
)

SECRET_VARIABLES = {
    variable
    for _, _, _, services in COMPOSE_SECRET_SPLIT
    for entries in services.values()
    for variable in entries.values()
}

_INTERPOLATION = re.compile(r"\$\{([A-Za-z0-9_]+)")


def _service_environment(service: dict) -> dict[str, str]:
    environment = service.get("environment") or {}
    if isinstance(environment, dict):
        return dict(environment)
    return dict(entry.split("=", 1) for entry in environment)


def test_base_compose_files_interpolate_no_secret() -> None:
    for base_name, _, _, _ in COMPOSE_SECRET_SPLIT:
        interpolations = _INTERPOLATION.findall((ROOT / base_name).read_text(encoding="utf-8"))
        leaked = SECRET_VARIABLES.intersection(interpolations)
        assert not leaked, f"{base_name} still interpolates secrets: {sorted(leaked)}"


def test_secrets_overlays_guard_every_secret_through_agent_secrets() -> None:
    for _, overlay_name, secret_set, services in COMPOSE_SECRET_SPLIT:
        overlay = yaml.safe_load((ROOT / overlay_name).read_text(encoding="utf-8"))
        for service_name, expected in services.items():
            environment = _service_environment(overlay["services"][service_name])
            for env_name, variable in expected.items():
                guard = f"{variable}:?run through agent-secrets run --set {secret_set}"
                assert guard in environment[env_name], (
                    f"{overlay_name}:{service_name}.{env_name} must be ${{{guard}}}"
                )
