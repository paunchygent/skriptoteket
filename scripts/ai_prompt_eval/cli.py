"""Command-line configuration for the live-backend prompt-eval harness."""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path

from scripts.ai_prompt_eval.fixture_bank import FIXTURES, EvalCapability, PromptEvalFixture

_CAPABILITIES: tuple[EvalCapability, ...] = ("inline_completion", "edit_suggestion")


@dataclass(frozen=True)
class HarnessConfig:
    base_url: str
    email: str
    password: str
    timeout_seconds: float
    artifacts_root: Path
    fixture_ids: tuple[str, ...]
    capabilities: frozenset[EvalCapability] | None


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
    """Resolve eval harness credentials (bootstrap superuser preferred)."""

    email = os.environ.get("BOOTSTRAP_SUPERUSER_EMAIL") or dotenv.get("BOOTSTRAP_SUPERUSER_EMAIL")
    password = os.environ.get("BOOTSTRAP_SUPERUSER_PASSWORD") or dotenv.get(
        "BOOTSTRAP_SUPERUSER_PASSWORD"
    )
    if email is not None or password is not None:
        return email, password

    email = os.environ.get("PLAYWRIGHT_EMAIL") or dotenv.get("PLAYWRIGHT_EMAIL")
    password = os.environ.get("PLAYWRIGHT_PASSWORD") or dotenv.get("PLAYWRIGHT_PASSWORD")
    return email, password


def parse_args() -> HarnessConfig:
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument(
        "--dotenv",
        default=os.environ.get("DOTENV_PATH") or ".env",
        help="Dotenv file for defaults (default: DOTENV_PATH env var or .env)",
    )
    pre_args, _ = pre_parser.parse_known_args()
    dotenv = _read_dotenv(Path(pre_args.dotenv))

    default_email, default_password = _get_credentials(dotenv=dotenv)

    parser = argparse.ArgumentParser(
        description="AI prompt evaluation harness (live backend)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        parents=[pre_parser],
    )
    parser.add_argument(
        "--base-url",
        default=_get_config_value(key="BASE_URL", dotenv=dotenv) or "http://127.0.0.1:8000",
        help="Backend base URL (FastAPI server).",
    )
    parser.add_argument(
        "--email",
        default=default_email,
        help=(
            "Login email (default: BOOTSTRAP_SUPERUSER_EMAIL, fallback PLAYWRIGHT_EMAIL, from env/dotenv)."
        ),
    )
    parser.add_argument(
        "--password",
        default=default_password,
        help=(
            "Login password (default: BOOTSTRAP_SUPERUSER_PASSWORD, fallback PLAYWRIGHT_PASSWORD, from env/dotenv)."
        ),
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=float(os.environ.get("AI_PROMPT_EVAL_TIMEOUT_SECONDS", "120")),
        help="HTTP request timeout per fixture.",
    )
    parser.add_argument(
        "--artifacts-root",
        default=".artifacts/ai-prompt-eval",
        help="Root folder for run artifacts (metadata only).",
    )
    parser.add_argument(
        "--fixture-id",
        action="append",
        default=[],
        help="Run only a specific fixture id (repeatable).",
    )
    parser.add_argument(
        "--capability",
        action="append",
        default=[],
        choices=_CAPABILITIES,
        help="Run only a capability (repeatable).",
    )

    args = parser.parse_args()

    if not args.email or not args.password:
        parser.error(
            "Missing credentials. Either:\n"
            "  1) Set BOOTSTRAP_SUPERUSER_EMAIL/BOOTSTRAP_SUPERUSER_PASSWORD in --dotenv (recommended)\n"
            "  2) Export them as environment variables\n"
            "  3) Pass --email and --password"
        )

    capabilities = frozenset(args.capability) if args.capability else None
    return HarnessConfig(
        base_url=args.base_url.rstrip("/"),
        email=args.email,
        password=args.password,
        timeout_seconds=args.timeout_seconds,
        artifacts_root=Path(args.artifacts_root),
        fixture_ids=tuple(args.fixture_id),
        capabilities=capabilities,
    )


def select_fixtures(
    *, fixture_ids: tuple[str, ...], capabilities: frozenset[EvalCapability] | None
) -> tuple[PromptEvalFixture, ...]:
    fixtures = FIXTURES
    if fixture_ids:
        allowed = set(fixture_ids)
        fixtures = tuple(f for f in fixtures if f.fixture_id in allowed)
    if capabilities:
        fixtures = tuple(f for f in fixtures if f.capability in capabilities)
    return fixtures
