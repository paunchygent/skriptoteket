"""Shared configuration for Playwright test scripts.

Reads from CLI args first, then environment variables, then a dotenv file.

We keep BOOTSTRAP_SUPERUSER_* for local provisioning, but Playwright smoke tests may use a different
account (e.g. admin in production) via PLAYWRIGHT_EMAIL / PLAYWRIGHT_PASSWORD or --email/--password.
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


def _get_credentials(*, dotenv: dict[str, str]) -> tuple[str | None, str | None]:
    """Resolve Playwright login credentials.

    Priority (high → low):
      1) PLAYWRIGHT_EMAIL / PLAYWRIGHT_PASSWORD
      2) BOOTSTRAP_SUPERUSER_EMAIL / BOOTSTRAP_SUPERUSER_PASSWORD (legacy default)
      3) Values from dotenv file (same keys, same priority order)
    """
    email = os.environ.get("PLAYWRIGHT_EMAIL") or dotenv.get("PLAYWRIGHT_EMAIL")
    password = os.environ.get("PLAYWRIGHT_PASSWORD") or dotenv.get("PLAYWRIGHT_PASSWORD")
    if email is not None or password is not None:
        return email, password

    email = os.environ.get("BOOTSTRAP_SUPERUSER_EMAIL") or dotenv.get("BOOTSTRAP_SUPERUSER_EMAIL")
    password = os.environ.get("BOOTSTRAP_SUPERUSER_PASSWORD") or dotenv.get(
        "BOOTSTRAP_SUPERUSER_PASSWORD"
    )
    return email, password


@dataclass(frozen=True)
class PlaywrightConfig:
    base_url: str
    email: str
    password: str


def get_config() -> PlaywrightConfig:
    """Parse CLI args with env var / .env fallbacks.

    Priority: CLI args > env vars > dotenv file > defaults.

    Usage:
        # Dev (uses .env defaults)
        pdm run ui-smoke

        # Prod (recommended): keep BOOTSTRAP_* for provisioning; use PLAYWRIGHT_* for smoke tests.
        pdm run ui-smoke --base-url https://skriptoteket.hule.education --dotenv .env.prod-smoke

        # Prod (explicit, no file changes)
        pdm run ui-smoke --base-url https://skriptoteket.hule.education \\
            --email admin@hule.education --password 'xxx'
    """
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument(
        "--dotenv",
        default=os.environ.get("DOTENV_PATH") or ".env",
        help="Dotenv file to read defaults from (default: DOTENV_PATH env var or .env)",
    )
    pre_args, _ = pre_parser.parse_known_args()
    dotenv = _read_dotenv(Path(pre_args.dotenv))

    default_email, default_password = _get_credentials(dotenv=dotenv)

    parser = argparse.ArgumentParser(
        description="Playwright smoke test",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[pre_parser],
    )
    parser.add_argument(
        "--base-url",
        default=_get_config_value(key="BASE_URL", dotenv=dotenv) or "http://127.0.0.1:8000",
        help="Base URL for the application (default: BASE_URL env var or http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--email",
        default=default_email,
        help=(
            "Login email (default: PLAYWRIGHT_EMAIL or BOOTSTRAP_SUPERUSER_EMAIL from env/dotenv)"
        ),
    )
    parser.add_argument(
        "--password",
        default=default_password,
        help=(
            "Login password (default: PLAYWRIGHT_PASSWORD or BOOTSTRAP_SUPERUSER_PASSWORD "
            "from env/dotenv)"
        ),
    )

    args = parser.parse_args()

    if not args.email or not args.password:
        parser.error(
            "Missing credentials. Either:\n"
            "  1. Set PLAYWRIGHT_EMAIL/PLAYWRIGHT_PASSWORD in --dotenv (recommended for prod)\n"
            "  2. Set BOOTSTRAP_SUPERUSER_EMAIL/BOOTSTRAP_SUPERUSER_PASSWORD in --dotenv (dev)\n"
            "  3. Export them as environment variables\n"
            "  4. Pass --email and --password CLI arguments"
        )

    return PlaywrightConfig(
        base_url=args.base_url,
        email=args.email,
        password=args.password,
    )
