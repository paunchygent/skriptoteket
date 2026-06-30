"""Story 58 Gateway stale-replay sensitive-input tests.

Domain purpose:
    Prove the production stale-replay proof can consume owner-scoped secrets
    from environment variables or private files instead of exposing them in the
    process argument list.

Relationships:
    - Exercises `scripts._story58_gateway_stale_replay_inputs`.
    - Protects the Story 58 proof helper used by
      `scripts.story58_gateway_stale_replay_proof`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts._story58_gateway_stale_replay_inputs import (
    resolve_story58_gateway_sensitive_inputs,
)


def test_sensitive_story58_inputs_resolve_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("STORY58_IDEMPOTENCY_KEY", "idem-from-env")
    monkeypatch.setenv("STORY58_OWNER_SCOPE", "identity:v1:user:sha256:owner")

    values = resolve_story58_gateway_sensitive_inputs(
        idempotency_key=None,
        idempotency_key_env="STORY58_IDEMPOTENCY_KEY",
        idempotency_key_file=None,
        expected_owner_scope=None,
        expected_owner_scope_env="STORY58_OWNER_SCOPE",
        expected_owner_scope_file=None,
    )

    assert values.idempotency_key == "idem-from-env"
    assert values.expected_owner_scope == "identity:v1:user:sha256:owner"


def test_sensitive_story58_inputs_resolve_from_private_files(tmp_path: Path) -> None:
    idempotency_file = tmp_path / "idempotency-key.txt"
    owner_scope_file = tmp_path / "owner-scope.txt"
    idempotency_file.write_text("idem-from-file\n", encoding="utf-8")
    owner_scope_file.write_text("identity:v1:user:sha256:file-owner\n", encoding="utf-8")

    values = resolve_story58_gateway_sensitive_inputs(
        idempotency_key=None,
        idempotency_key_env=None,
        idempotency_key_file=idempotency_file,
        expected_owner_scope=None,
        expected_owner_scope_env=None,
        expected_owner_scope_file=owner_scope_file,
    )

    assert values.idempotency_key == "idem-from-file"
    assert values.expected_owner_scope == "identity:v1:user:sha256:file-owner"


def test_sensitive_story58_inputs_fail_before_browser_when_missing() -> None:
    with pytest.raises(SystemExit, match="Missing Story 58 idempotency key"):
        resolve_story58_gateway_sensitive_inputs(
            idempotency_key=None,
            idempotency_key_env="STORY58_IDEMPOTENCY_KEY_DOES_NOT_EXIST",
            idempotency_key_file=None,
            expected_owner_scope="identity:v1:user:sha256:owner",
            expected_owner_scope_env=None,
            expected_owner_scope_file=None,
        )
