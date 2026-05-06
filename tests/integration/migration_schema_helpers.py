"""Shared schema probes for Alembic migration assertions.

Purpose:
    Provide small PostgreSQL information-schema helpers for revision-specific
    migration tests.

Relationships:
    - Used by migration assertion modules under `tests/integration`.
    - Keeps SQL inspection details out of individual revision checks.
"""

from collections.abc import Awaitable, Callable

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

RevisionAssertion = Callable[[AsyncEngine], Awaitable[None]]


async def table_names(engine: AsyncEngine) -> set[str]:
    """Return public table names for the current test database."""

    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        )
        return {row[0] for row in result.fetchall()}


async def column_map(engine: AsyncEngine, table_name: str) -> dict[str, dict[str, object]]:
    """Return nullable metadata for columns in one public table."""

    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                """
                SELECT column_name, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = :table_name
                """
            ),
            {"table_name": table_name},
        )
        return {row.column_name: {"is_nullable": row.is_nullable} for row in result.fetchall()}


async def column_defaults(engine: AsyncEngine, table_name: str) -> dict[str, str | None]:
    """Return column defaults for one public table."""

    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                """
                SELECT column_name, column_default
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = :table_name
                """
            ),
            {"table_name": table_name},
        )
        return {row.column_name: row.column_default for row in result.fetchall()}


async def index_names(engine: AsyncEngine, table_name: str) -> set[str]:
    """Return index names for one public table."""

    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                """
                SELECT indexname
                FROM pg_indexes
                WHERE schemaname = 'public' AND tablename = :table_name
                """
            ),
            {"table_name": table_name},
        )
        return {row[0] for row in result.fetchall()}


async def index_definitions(engine: AsyncEngine, table_name: str) -> dict[str, str]:
    """Return PostgreSQL index definitions by index name."""

    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                """
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE schemaname = 'public' AND tablename = :table_name
                """
            ),
            {"table_name": table_name},
        )
        return {row.indexname: row.indexdef for row in result.fetchall()}


async def foreign_key_targets(engine: AsyncEngine, table_name: str) -> dict[str, str]:
    """Return referred table names by constrained column."""

    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                """
                SELECT kcu.column_name, ccu.table_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                 AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage ccu
                  ON ccu.constraint_name = tc.constraint_name
                 AND ccu.table_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY'
                  AND tc.table_schema = 'public'
                  AND tc.table_name = :table_name
                """
            ),
            {"table_name": table_name},
        )
        return {row[0]: row[1] for row in result.fetchall()}


async def foreign_key_delete_rules(engine: AsyncEngine, table_name: str) -> dict[str, str]:
    """Return referential delete rules by constrained column."""

    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                """
                SELECT kcu.column_name, rc.delete_rule
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                 AND tc.table_schema = kcu.table_schema
                JOIN information_schema.referential_constraints rc
                  ON rc.constraint_name = tc.constraint_name
                 AND rc.constraint_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY'
                  AND tc.table_schema = 'public'
                  AND tc.table_name = :table_name
                """
            ),
            {"table_name": table_name},
        )
        return {row[0]: row[1] for row in result.fetchall()}


async def check_constraint_names(engine: AsyncEngine, table_name: str) -> set[str]:
    """Return check constraint names for one public table."""

    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                """
                SELECT constraint_name
                FROM information_schema.table_constraints
                WHERE table_schema = 'public'
                  AND table_name = :table_name
                  AND constraint_type = 'CHECK'
                """
            ),
            {"table_name": table_name},
        )
        return {row[0] for row in result.fetchall()}


async def scalar_count(engine: AsyncEngine, table_name: str) -> int:
    """Return the row count for one public table."""

    async with engine.connect() as conn:
        result = await conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
        return int(result.scalar_one())
