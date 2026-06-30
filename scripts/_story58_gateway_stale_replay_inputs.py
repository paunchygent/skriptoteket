"""Story 58 Gateway stale-replay private input resolution.

Domain purpose:
    Resolve owner-scoped stale-replay proof secrets from CLI, environment, or
    private files before the authenticated Gateway proof starts.

Relationships:
    - Used by `scripts.story58_gateway_stale_replay_proof`.
    - Keeps sensitive idempotency and owner-scope values out of retained proof
      artifacts and allows operators to avoid process-argument exposure.
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_IDEMPOTENCY_KEY_ENV = "STORY58_IDEMPOTENCY_KEY"
DEFAULT_OWNER_SCOPE_ENV = "STORY58_OWNER_SCOPE"


@dataclass(frozen=True)
class Story58GatewaySensitiveInputs:
    """Resolved sensitive values needed for one stale-replay proof run."""

    idempotency_key: str
    expected_owner_scope: str


def add_story58_gateway_sensitive_input_args(parser: argparse.ArgumentParser) -> None:
    """Register private stale-replay input arguments on a proof CLI parser."""

    parser.add_argument("--idempotency-key", default=None)
    parser.add_argument("--idempotency-key-env", default=DEFAULT_IDEMPOTENCY_KEY_ENV)
    parser.add_argument("--idempotency-key-file", type=Path, default=None)
    parser.add_argument("--expected-owner-scope", default=None)
    parser.add_argument("--expected-owner-scope-env", default=DEFAULT_OWNER_SCOPE_ENV)
    parser.add_argument("--expected-owner-scope-file", type=Path, default=None)


def resolve_story58_gateway_sensitive_inputs(
    *,
    idempotency_key: str | None,
    idempotency_key_env: str | None,
    idempotency_key_file: Path | None,
    expected_owner_scope: str | None,
    expected_owner_scope_env: str | None,
    expected_owner_scope_file: Path | None,
) -> Story58GatewaySensitiveInputs:
    """Resolve required Story 58 stale-replay sensitive inputs."""

    return Story58GatewaySensitiveInputs(
        idempotency_key=_resolve_sensitive_value(
            label="Story 58 idempotency key",
            cli_value=idempotency_key,
            env_name=idempotency_key_env,
            file_path=idempotency_key_file,
        ),
        expected_owner_scope=_resolve_sensitive_value(
            label="Story 58 expected owner scope",
            cli_value=expected_owner_scope,
            env_name=expected_owner_scope_env,
            file_path=expected_owner_scope_file,
        ),
    )


def _resolve_sensitive_value(
    *,
    label: str,
    cli_value: str | None,
    env_name: str | None,
    file_path: Path | None,
) -> str:
    cli_candidate = _non_empty(cli_value)
    if cli_candidate is not None:
        return cli_candidate
    if env_name is not None:
        env_candidate = _non_empty(os.environ.get(env_name))
        if env_candidate is not None:
            return env_candidate
    if file_path is not None:
        file_candidate = _non_empty(file_path.read_text(encoding="utf-8"))
        if file_candidate is not None:
            return file_candidate
    sources = _source_description(env_name=env_name, file_path=file_path)
    raise SystemExit(f"Missing {label}; provide CLI value, {sources}.")


def _source_description(*, env_name: str | None, file_path: Path | None) -> str:
    parts: list[str] = []
    if env_name is not None:
        parts.append(f"env {env_name}")
    if file_path is not None:
        parts.append(f"file {file_path}")
    if not parts:
        return "or configure an env/file source"
    return " or ".join(parts)


def _non_empty(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped else None
