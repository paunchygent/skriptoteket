"""Configuration for the TASK-0376 production protected API browser proof.

Purpose:
    Resolve the proof's origins, credentials source and artifact directory from
    the command line, the environment and an optional dotenv file, without
    exposing credentials.

Relationships:
    Used by `scripts.playwright_task_0376_production_protected_api`.
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence
from urllib.parse import urlparse

DEFAULT_BASE_URL = "https://skriptoteket.hule.education"
DEFAULT_HULEEDU_AUTH_ORIGIN = "https://api.hule.education"
DEFAULT_HULEEDU_LOGIN_ORIGIN = "https://hule.education"
DEFAULT_DOTENV_PATH = ".env.prod-smoke"
ARTIFACT_ROOT = Path(".artifacts/playwright-task-0376-production-protected-api")


@dataclass(frozen=True)
class ProofConfig:
    """Resolved proof configuration without credential exposure."""

    base_url: str
    huleedu_auth_origin: str
    huleedu_login_origin: str
    artifact_root: Path
    email: str
    password: str


def _read_dotenv(path: Path) -> dict[str, str]:
    """Read simple dotenv files without evaluating shell syntax."""
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _normalize_origin(value: str, *, field_name: str) -> str:
    """Validate and normalize an origin-like URL."""
    normalized = value.rstrip("/")
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.path:
        raise SystemExit(f"Invalid {field_name}: {value}")
    return normalized


def _config_value(
    *,
    cli_value: str | None,
    env_key: str,
    dotenv: dict[str, str],
    default: str,
) -> str:
    """Resolve one config value from CLI, env, dotenv, then default."""
    return cli_value or os.environ.get(env_key) or dotenv.get(env_key) or default


def parse_args(argv: Sequence[str] | None = None) -> ProofConfig:
    """Parse CLI and dotenv-backed proof config."""
    parser = argparse.ArgumentParser(description="TASK-0376 production protected API proof")
    parser.add_argument("--dotenv", default=os.environ.get("DOTENV_PATH") or DEFAULT_DOTENV_PATH)
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--huleedu-auth-origin", default=None)
    parser.add_argument("--huleedu-login-origin", default=None)
    parser.add_argument("--artifact-dir", default=None)
    parser.add_argument("--email", default=None)
    parser.add_argument("--password", default=None)
    args = parser.parse_args(argv)

    dotenv = _read_dotenv(Path(args.dotenv))
    email = args.email or os.environ.get("PLAYWRIGHT_EMAIL") or dotenv.get("PLAYWRIGHT_EMAIL")
    password = (
        args.password or os.environ.get("PLAYWRIGHT_PASSWORD") or dotenv.get("PLAYWRIGHT_PASSWORD")
    )
    if not email or not password:
        parser.error("Missing credentials. Provide --email/--password or PLAYWRIGHT_* values.")

    return ProofConfig(
        base_url=_normalize_origin(
            _config_value(
                cli_value=args.base_url,
                env_key="BASE_URL",
                dotenv=dotenv,
                default=DEFAULT_BASE_URL,
            ),
            field_name="--base-url",
        ),
        huleedu_auth_origin=_normalize_origin(
            _config_value(
                cli_value=args.huleedu_auth_origin,
                env_key="HULEEDU_AUTH_ORIGIN",
                dotenv=dotenv,
                default=DEFAULT_HULEEDU_AUTH_ORIGIN,
            ),
            field_name="--huleedu-auth-origin",
        ),
        huleedu_login_origin=_normalize_origin(
            _config_value(
                cli_value=args.huleedu_login_origin,
                env_key="HULEEDU_LOGIN_ORIGIN",
                dotenv=dotenv,
                default=DEFAULT_HULEEDU_LOGIN_ORIGIN,
            ),
            field_name="--huleedu-login-origin",
        ),
        artifact_root=Path(args.artifact_dir).expanduser() if args.artifact_dir else ARTIFACT_ROOT,
        email=email,
        password=password,
    )
