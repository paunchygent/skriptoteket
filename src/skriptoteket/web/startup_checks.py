"""Startup checks for the FastAPI web application.

Purpose:
    Fail fast when the running web process is pointed at a database schema that
    does not match the repository's Alembic heads or is missing required
    classroom-planner smart-rule tables and foreign keys despite claiming the
    latest revision.

Relationships:
    - Called from `skriptoteket.web.app` during FastAPI startup.
    - Reads the repository's Alembic graph from `alembic.ini`.
    - Connects to the configured PostgreSQL database through SQLAlchemy.
"""

from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine

from skriptoteket.config import Settings

_REPO_ROOT = Path(__file__).resolve().parents[3]
_ALEMBIC_INI_PATH = _REPO_ROOT / "alembic.ini"
_ROSTER_SMART_RULE_ROOT_TABLE = "classroom_planner_roster_smart_rule_sets"
_ROSTER_SMART_RULE_CHILD_TABLES = (
    "classroom_planner_roster_seating_preferences",
    "classroom_planner_roster_relationship_rules",
)


def _load_repo_head_revisions() -> tuple[str, ...]:
    """Return the Alembic head revisions declared by the current repository."""

    config = Config(str(_ALEMBIC_INI_PATH))
    script = ScriptDirectory.from_config(config)
    return tuple(sorted(script.get_heads()))


async def _load_database_revisions(database_url: str) -> tuple[str, ...]:
    """Return the revisions recorded in the target database."""

    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        async with engine.connect() as connection:
            result = await connection.execute(
                text("SELECT version_num FROM alembic_version ORDER BY version_num")
            )
            return tuple(row[0] for row in result.fetchall())
    finally:
        await engine.dispose()


async def _load_database_schema_contract(
    database_url: str,
) -> tuple[frozenset[str], dict[str, tuple[str, ...]]]:
    """Return required smart-rule tables and their live roster-id FK targets."""

    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        async with engine.connect() as connection:

            def inspect_contract(
                sync_connection,
            ) -> tuple[frozenset[str], dict[str, tuple[str, ...]]]:
                inspector = inspect(sync_connection)
                table_names = frozenset(inspector.get_table_names())
                foreign_key_targets: dict[str, tuple[str, ...]] = {}
                for table_name in _ROSTER_SMART_RULE_CHILD_TABLES:
                    if table_name not in table_names:
                        foreign_key_targets[table_name] = ()
                        continue
                    targets = sorted(
                        fk["referred_table"]
                        for fk in inspector.get_foreign_keys(table_name)
                        if fk.get("constrained_columns") == ["roster_id"]
                    )
                    foreign_key_targets[table_name] = tuple(targets)
                return table_names, foreign_key_targets

            return await connection.run_sync(inspect_contract)
    finally:
        await engine.dispose()


def _assert_database_revision_is_current(
    *,
    expected_heads: tuple[str, ...],
    current_revisions: tuple[str, ...],
) -> None:
    """Raise when the live database does not match the repo's Alembic heads."""

    if current_revisions == expected_heads:
        return
    expected = ", ".join(expected_heads) or "<none>"
    current = ", ".join(current_revisions) or "<none>"
    raise RuntimeError(
        "Database schema is not at the required Alembic revision. "
        f"Current: {current}. Expected: {expected}. "
        "Run `pdm run db-upgrade` before starting the web app."
    )


def _assert_roster_smart_rule_schema_is_current(
    *,
    table_names: frozenset[str],
    foreign_key_targets: dict[str, tuple[str, ...]],
) -> None:
    """Raise when smart-rule tables or FKs do not match the current contract."""

    required_tables = {_ROSTER_SMART_RULE_ROOT_TABLE, *_ROSTER_SMART_RULE_CHILD_TABLES}
    missing_tables = sorted(required_tables - set(table_names))
    if missing_tables:
        raise RuntimeError(
            "Database schema is missing required classroom planner smart-rule tables "
            f"despite matching the recorded Alembic revision: {', '.join(missing_tables)}. "
            "Run `pdm run db-upgrade` before starting the web app."
        )

    broken_tables = [
        table_name
        for table_name in _ROSTER_SMART_RULE_CHILD_TABLES
        if foreign_key_targets.get(table_name) != (_ROSTER_SMART_RULE_ROOT_TABLE,)
    ]
    if not broken_tables:
        return
    details = ", ".join(
        f"{table_name} -> {foreign_key_targets.get(table_name, ()) or ('<missing>',)}"
        for table_name in broken_tables
    )
    raise RuntimeError(
        "Database schema has an outdated classroom planner smart-rule foreign-key contract "
        f"despite matching the recorded Alembic revision: {details}. "
        "Run `pdm run db-upgrade` before starting the web app."
    )


async def ensure_database_revision_is_current(settings: Settings) -> None:
    """Fail startup when the configured database schema is stale or inconsistent."""

    expected_heads = _load_repo_head_revisions()
    current_revisions = await _load_database_revisions(settings.DATABASE_URL)
    _assert_database_revision_is_current(
        expected_heads=expected_heads,
        current_revisions=current_revisions,
    )
    table_names, foreign_key_targets = await _load_database_schema_contract(settings.DATABASE_URL)
    _assert_roster_smart_rule_schema_is_current(
        table_names=table_names,
        foreign_key_targets=foreign_key_targets,
    )
