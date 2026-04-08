"""Integration coverage for the guest-upgrade consumption ledger migration.

Purpose:
    Verify the `0f4c2d7a9b1e` Alembic revision remains idempotent and leaves the
    guest-upgrade consumption ledger with the expected schema after repeated
    upgrade cycles.

Relationships:
    - Exercises
      `migrations/versions/0f4c2d7a9b1e_add_classroom_planner_guest_upgrade_consumption.py`.
    - Counts as the dedicated migration coverage for the latest guest-upgrade
      consumption head.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from testcontainers.postgres import PostgresContainer

from tests.integration.migration_idempotency_support import assert_revision_is_idempotent

_REVISION_ID = "0f4c2d7a9b1e"


async def _assert_guest_upgrade_consumption_schema(engine: AsyncEngine) -> None:
    async with engine.connect() as conn:
        columns = await conn.execute(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'classroom_planner_guest_upgrade_consumptions'
                ORDER BY ordinal_position
                """
            )
        )
        indexes = await conn.execute(
            text(
                """
                SELECT indexname
                FROM pg_indexes
                WHERE schemaname = 'public'
                  AND tablename = 'classroom_planner_guest_upgrade_consumptions'
                """
            )
        )

    assert [row[0] for row in columns.fetchall()] == [
        "id",
        "owner_user_id",
        "app_id",
        "snapshot_id",
        "consumed_at",
    ]
    assert {
        "classroom_planner_guest_upgrade_consumptions_pkey",
        "uq_cp_guest_upgrade_consumptions_owner_app",
        "ix_classroom_planner_guest_upgrade_consumptions_owner_user_id",
    } <= {row[0] for row in indexes.fetchall()}


@pytest.mark.docker
def test_migration_0f4c2d7a9b1e_is_idempotent(
    postgres_container: PostgresContainer,
) -> None:
    assert_revision_is_idempotent(
        postgres_container=postgres_container,
        revision_id=_REVISION_ID,
        schema_assertion=_assert_guest_upgrade_consumption_schema,
    )
