"""Prove guest draft IDs are unique after migration."""

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

from tests.fixtures.database_fixtures import PooledDatabase
from tests.integration.migration_idempotency_support import assert_revision_is_idempotent
from tests.integration.test_migration_c8e4f2a6d9b3_idempotent import _primary_key_columns

pytestmark = [pytest.mark.integration, pytest.mark.docker]


async def _assert_schema(engine: AsyncEngine) -> None:
    assert await _primary_key_columns(engine) == ["draft_id"]


def test_claim_key_migration_is_idempotent(empty_module_database: PooledDatabase) -> None:
    assert_revision_is_idempotent(
        empty_module_database=empty_module_database,
        revision_id="f2b9c4d8a701",
        schema_assertion=_assert_schema,
    )


def test_upgrade_removes_old_duplicate_claims(fresh_database: PooledDatabase) -> None:
    import asyncio
    from uuid import uuid4

    from alembic import command
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    from tests.fixtures.database_fixtures import alembic_config_for

    url = fresh_database.url
    config = alembic_config_for(database_url=url)
    command.upgrade(config, "aa30c309b36c")

    async def seed_and_check(*, seed: bool) -> None:
        engine = create_async_engine(url)
        try:
            async with engine.begin() as connection:
                if seed:
                    draft = uuid4()
                    for number in (1, 2):
                        owner = uuid4()
                        await connection.execute(
                            text(
                                "INSERT INTO users (id, email, role, auth_provider) "
                                "VALUES (:id, :email, 'guest', 'local')"
                            ),
                            {"id": owner, "email": f"claim-{number}@example.com"},
                        )
                        await connection.execute(
                            text(
                                "INSERT INTO exam_guest_draft_handoffs "
                                "(owner_user_id, draft_id, lineage_id, created_at) "
                                "VALUES (:owner, :draft, :lineage, now())"
                            ),
                            {"owner": owner, "draft": draft, "lineage": uuid4()},
                        )
                else:
                    assert (
                        await connection.scalar(
                            text("SELECT count(*) FROM exam_guest_draft_handoffs")
                        )
                        == 0
                    )
        finally:
            await engine.dispose()

    asyncio.run(seed_and_check(seed=True))
    command.upgrade(config, "f2b9c4d8a701")
    asyncio.run(seed_and_check(seed=False))
