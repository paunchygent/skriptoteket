"""The ``migrated_db`` fixture fails test setup with the migration thread's exception."""

from __future__ import annotations

from typing import Any

import pytest
from alembic.config import Config

from tests.fixtures import database_fixtures


@pytest.mark.unit
def test_migration_error_in_thread_fails_migrated_db_setup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class MigrationBoom(Exception):
        pass

    def failing_upgrade(config: Config, revision: str) -> None:
        raise MigrationBoom(f"upgrade to {revision} failed")

    monkeypatch.setenv("DATABASE_URL", "unset-by-test")
    monkeypatch.setattr(database_fixtures.command, "upgrade", failing_upgrade)
    fixture_body: Any = getattr(database_fixtures.migrated_db, "__wrapped__")

    with pytest.raises(MigrationBoom, match="upgrade to head failed"):
        fixture_body(Config(), "postgresql+asyncpg://unused")


@pytest.mark.unit
def test_successful_migration_returns_the_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    upgrades: list[str] = []
    monkeypatch.setenv("DATABASE_URL", "unset-by-test")
    monkeypatch.setattr(
        database_fixtures.command, "upgrade", lambda config, revision: upgrades.append(revision)
    )
    fixture_body: Any = getattr(database_fixtures.migrated_db, "__wrapped__")

    assert fixture_body(Config(), "postgresql+asyncpg://unused") == "postgresql+asyncpg://unused"
    assert upgrades == ["head"]
