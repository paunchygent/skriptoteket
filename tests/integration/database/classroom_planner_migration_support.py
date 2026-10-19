"""Support for the classroom planner migration test: legacy seed, queries, thread runner.

Holds the legacy (pre-slice-two) data producer, the read-only schema and data
queries, and the threaded Alembic runner used by
``test_classroom_planner_migration.py``.
"""

import json
import threading
from collections.abc import Callable
from dataclasses import dataclass
from uuid import uuid4

from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


def run_alembic_cmd(
    alembic_cfg: Config,
    cmd_func: Callable[[Config, str], None],
    revision: str,
) -> None:
    """Run one Alembic command in its own thread so env.py may start its own event loop."""
    errors: list[BaseException] = []

    def run_command() -> None:
        try:
            cmd_func(alembic_cfg, revision)
        except BaseException as exc:  # noqa: BLE001 - thread boundary re-raises below.
            errors.append(exc)

    thread = threading.Thread(target=run_command)
    thread.start()
    thread.join()
    if errors:
        raise errors[0]


async def get_tables(engine: AsyncEngine) -> set[str]:
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        )
        return {row[0] for row in result.fetchall()}


async def get_columns(engine: AsyncEngine, table_name: str) -> set[str]:
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = :table_name
                """
            ),
            {"table_name": table_name},
        )
        return {row[0] for row in result.fetchall()}


async def get_backfilled_group_rows(
    engine: AsyncEngine, draft_id: str
) -> list[tuple[str, str, int]]:
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                """
                SELECT group_id, name, sort_order
                FROM classroom_planner_draft_groups
                WHERE draft_id = :draft_id
                ORDER BY sort_order
                """
            ),
            {"draft_id": draft_id},
        )
        return [(row[0], row[1], row[2]) for row in result.fetchall()]


async def get_group_assignment_ids(engine: AsyncEngine, draft_id: str) -> list[str]:
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                """
                SELECT group_id
                FROM classroom_planner_group_assignments
                WHERE draft_id = :draft_id
                ORDER BY student_id
                """
            ),
            {"draft_id": draft_id},
        )
        return [row[0] for row in result.fetchall()]


async def get_owner_draft_statuses(engine: AsyncEngine, owner_id: str) -> list[str]:
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                """
                SELECT status
                FROM classroom_planner_plan_drafts
                WHERE owner_user_id = :owner_user_id
                ORDER BY updated_at DESC, created_at DESC
                """
            ),
            {"owner_user_id": owner_id},
        )
        return [row[0] for row in result.fetchall()]


async def get_index_names(engine: AsyncEngine, table_name: str) -> set[str]:
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


@dataclass(frozen=True, slots=True)
class SeededLegacyPlanner:
    """Identifiers of the rows seeded at the pre-slice-two revision."""

    draft_id: str
    second_draft_id: str
    owner_id: str
    roster_id: str
    template_id: str


async def seed_pre_slice_two_draft(
    async_engine: AsyncEngine,
) -> SeededLegacyPlanner:
    owner_id = str(uuid4())
    roster_id = str(uuid4())
    template_id = str(uuid4())
    draft_id = str(uuid4())
    second_draft_id = str(uuid4())

    async with async_engine.begin() as conn:
        await conn.execute(
            text(
                """
                INSERT INTO users (
                    id,
                    email,
                    role,
                    auth_provider,
                    password_hash,
                    is_active,
                    email_verified,
                    failed_login_attempts
                )
                VALUES (
                    :id,
                    :email,
                    'superuser',
                    'local',
                    'hash',
                    true,
                    true,
                    0
                )
                """
            ),
            {
                "id": owner_id,
                "email": f"{owner_id}@example.test",
            },
        )
        await conn.execute(
            text(
                """
                INSERT INTO classroom_planner_rosters (id, owner_user_id, name, students)
                VALUES (:id, :owner_user_id, 'Klass 7A', CAST(:students AS jsonb))
                """
            ),
            {
                "id": roster_id,
                "owner_user_id": owner_id,
                "students": json.dumps(
                    [
                        {"id": "s1", "display_name": "Ada"},
                        {"id": "s2", "display_name": "Bo"},
                    ]
                ),
            },
        )
        await conn.execute(
            text(
                """
                INSERT INTO classroom_planner_room_templates (id, owner_user_id, name, seats)
                VALUES (:id, :owner_user_id, 'Sal 101', CAST(:seats AS jsonb))
                """
            ),
            {
                "id": template_id,
                "owner_user_id": owner_id,
                "seats": json.dumps(
                    [
                        {"id": "seat-1", "x": 1, "y": 1},
                        {"id": "seat-2", "x": 2, "y": 1},
                    ]
                ),
            },
        )
        await conn.execute(
            text(
                """
                INSERT INTO classroom_planner_plan_drafts (
                    id,
                    owner_user_id,
                    roster_id,
                    template_id,
                    lesson_mode_id,
                    revision,
                    group_count
                )
                VALUES (
                    :id,
                    :owner_user_id,
                    :roster_id,
                    :template_id,
                    'group_work',
                    0,
                    2
                )
                """
            ),
            {
                "id": draft_id,
                "owner_user_id": owner_id,
                "roster_id": roster_id,
                "template_id": template_id,
            },
        )
        await conn.execute(
            text(
                """
                INSERT INTO classroom_planner_plan_drafts (
                    id,
                    owner_user_id,
                    roster_id,
                    template_id,
                    lesson_mode_id,
                    revision,
                    group_count
                )
                VALUES (
                    :id,
                    :owner_user_id,
                    :roster_id,
                    :template_id,
                    'group_work',
                    0,
                    1
                )
                """
            ),
            {
                "id": second_draft_id,
                "owner_user_id": owner_id,
                "roster_id": roster_id,
                "template_id": template_id,
            },
        )
        await conn.execute(
            text(
                """
                UPDATE classroom_planner_plan_drafts
                SET updated_at = now() + interval '1 minute'
                WHERE id = :draft_id
                """
            ),
            {"draft_id": second_draft_id},
        )
        await conn.execute(
            text(
                """
                INSERT INTO classroom_planner_group_assignments (draft_id, student_id, group_id)
                VALUES (:draft_id, 's1', 'group-1'), (:draft_id, 's2', 'group-2')
                """
            ),
            {"draft_id": draft_id},
        )

    return SeededLegacyPlanner(
        draft_id=draft_id,
        second_draft_id=second_draft_id,
        owner_id=owner_id,
        roster_id=roster_id,
        template_id=template_id,
    )


async def insert_second_roster_with_active_drafts(
    engine: AsyncEngine,
    *,
    owner_id: str,
    roster_id: str,
) -> None:
    second_roster_id = str(uuid4())
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                INSERT INTO classroom_planner_rosters (id, owner_user_id, name, students)
                VALUES (:id, :owner_user_id, 'Klass 7B', CAST(:students AS jsonb))
                """
            ),
            {
                "id": second_roster_id,
                "owner_user_id": owner_id,
                "students": json.dumps([{"id": "s3", "display_name": "Cia"}]),
            },
        )
        await conn.execute(
            text(
                """
                INSERT INTO classroom_planner_plan_drafts (
                    id,
                    owner_user_id,
                    roster_id,
                    draft_kind,
                    template_id,
                    status,
                    revision,
                    last_opened_at
                )
                VALUES (
                    :id,
                    :owner_user_id,
                    :roster_id,
                    'seating',
                    NULL,
                    'active',
                    0,
                    now()
                )
                """
            ),
            {
                "id": str(uuid4()),
                "owner_user_id": owner_id,
                "roster_id": second_roster_id,
            },
        )
        await conn.execute(
            text(
                """
                INSERT INTO classroom_planner_plan_drafts (
                    id,
                    owner_user_id,
                    roster_id,
                    draft_kind,
                    template_id,
                    status,
                    revision,
                    last_opened_at
                )
                VALUES (
                    :id,
                    :owner_user_id,
                    :roster_id,
                    'grouping',
                    NULL,
                    'active',
                    0,
                    now()
                )
                """
            ),
            {
                "id": str(uuid4()),
                "owner_user_id": owner_id,
                "roster_id": roster_id,
            },
        )


async def insert_active_grouping_draft(
    engine: AsyncEngine,
    *,
    owner_id: str,
    roster_id: str,
) -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                INSERT INTO classroom_planner_plan_drafts (
                    id,
                    owner_user_id,
                    roster_id,
                    draft_kind,
                    template_id,
                    status,
                    revision,
                    last_opened_at
                )
                VALUES (
                    :id,
                    :owner_user_id,
                    :roster_id,
                    'grouping',
                    NULL,
                    'active',
                    0,
                    now()
                )
                """
            ),
            {
                "id": str(uuid4()),
                "owner_user_id": owner_id,
                "roster_id": roster_id,
            },
        )
