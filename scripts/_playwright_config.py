"""Shared configuration for Playwright test scripts.

Reads from CLI args first, then environment variables, then .env file.
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path


def _read_dotenv(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _get_config_value(*, key: str, dotenv: dict[str, str]) -> str | None:
    return os.environ.get(key) or dotenv.get(key)


@dataclass(frozen=True)
class PlaywrightConfig:
    base_url: str
    email: str
    password: str


def get_config() -> PlaywrightConfig:
    """Parse CLI args with env var / .env fallbacks.

    Priority: CLI args > env vars > .env file > defaults.

    Usage:
        # Dev (uses .env defaults)
        pdm run ui-smoke

        # Prod (explicit, no file changes)
        pdm run ui-smoke --base-url https://skriptoteket.hule.education \\
            --email admin@hule.education --password 'xxx'
    """
    dotenv = _read_dotenv(Path(".env"))

    parser = argparse.ArgumentParser(
        description="Playwright smoke test",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--base-url",
        default=_get_config_value(key="BASE_URL", dotenv=dotenv) or "http://127.0.0.1:8000",
        help="Base URL for the application (default: BASE_URL env var or http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--email",
        default=_get_config_value(key="BOOTSTRAP_SUPERUSER_EMAIL", dotenv=dotenv),
        help="Login email (default: BOOTSTRAP_SUPERUSER_EMAIL env var)",
    )
    parser.add_argument(
        "--password",
        default=_get_config_value(key="BOOTSTRAP_SUPERUSER_PASSWORD", dotenv=dotenv),
        help="Login password (default: BOOTSTRAP_SUPERUSER_PASSWORD env var)",
    )

    args = parser.parse_args()

    if not args.email or not args.password:
        parser.error(
            "Missing credentials. Either:\n"
            "  1. Set BOOTSTRAP_SUPERUSER_EMAIL/BOOTSTRAP_SUPERUSER_PASSWORD in .env\n"
            "  2. Export them as environment variables\n"
            "  3. Pass --email and --password CLI arguments"
        )

    return PlaywrightConfig(
        base_url=args.base_url,
        email=args.email,
        password=args.password,
    )
