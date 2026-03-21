"""Integration coverage for classroom planner schema migrations.

This module verifies that the Slice 2 classroom planner schema upgrades cleanly
to the latest head, tolerates a no-op re-upgrade, backfills draft groups from
the previous draft shape, and can be downgraded and upgraded again without
leaving the database in a partial state.
"""

import json
import os
import threading
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from tests.fixtures.database_fixtures import _to_async_database_url


@pytest.mark.integration
@pytest.mark.docker
@pytest.mark.asyncio
async def test_classroom_planner_migration_idempotency(postgres_container):
    """Verify Slice 2 head migration, backfill behavior, and clean re-upgrades."""
    database_url = _to_async_database_url(postgres_container.get_connection_url())
    os.environ["DATABASE_URL"] = database_url

    alembic_cfg = Config(str(Path("alembic.ini")))
    alembic_cfg.set_main_option("sqlalchemy.url", database_url)

    target_revision = "d8f0d0ef2b6d"
    pre_slice_two_revision = "4f5605f8be18"
    base_revision = "0032_user_file_vault"

    def run_alembic_cmd(cmd_func, *args):
        thread = threading.Thread(target=cmd_func, args=(alembic_cfg, *args))
        thread.start()
        thread.join()

    engine = create_async_engine(_to_async_database_url(database_url))

    async def get_tables() -> set[str]:
        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
            )
            return {row[0] for row in result.fetchall()}

    async def get_columns(table_name: str) -> set[str]:
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

    async def seed_pre_slice_two_draft(async_engine: AsyncEngine) -> tuple[str, str, str]:
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
                        external_id,
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
                        :external_id,
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
                    "external_id": owner_id,
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

        return draft_id, second_draft_id, owner_id

    async def get_backfilled_group_rows(draft_id: str) -> list[tuple[str, str, int]]:
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

    async def get_group_assignment_ids(draft_id: str) -> list[str]:
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

    async def get_owner_draft_statuses(owner_id: str) -> list[str]:
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

    async def get_index_names(table_name: str) -> set[str]:
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

    try:
        run_alembic_cmd(command.upgrade, pre_slice_two_revision)
        draft_id, second_draft_id, owner_id = await seed_pre_slice_two_draft(engine)

        run_alembic_cmd(command.upgrade, target_revision)

        tables = await get_tables()
        assert {
            "classroom_planner_rosters",
            "classroom_planner_room_templates",
            "classroom_planner_plan_drafts",
            "classroom_planner_group_assignments",
            "classroom_planner_seat_assignments",
            "classroom_planner_draft_groups",
            "classroom_planner_student_planning_meta",
            "classroom_planner_pair_constraints",
            "classroom_planner_planning_profiles",
            "classroom_planner_arrangement_snapshots",
        }.issubset(tables)

        assert "fixtures" in await get_columns("classroom_planner_room_templates")
        assert "engine_metadata" in await get_columns("classroom_planner_plan_drafts")
        assert "status" in await get_columns("classroom_planner_plan_drafts")
        assert "last_opened_at" in await get_columns("classroom_planner_plan_drafts")
        assert "group_count" not in await get_columns("classroom_planner_plan_drafts")
        assert "uq_cp_active_draft_owner" in await get_index_names("classroom_planner_plan_drafts")

        backfilled_groups = await get_backfilled_group_rows(draft_id)
        assert backfilled_groups == [
            (f"group-1-{draft_id.replace('-', '')[:8]}", "Grupp 1", 0),
            (f"group-2-{draft_id.replace('-', '')[:8]}", "Grupp 2", 1),
        ]
        assert await get_group_assignment_ids(draft_id) == [
            f"group-1-{draft_id.replace('-', '')[:8]}",
            f"group-2-{draft_id.replace('-', '')[:8]}",
        ]
        assert await get_backfilled_group_rows(second_draft_id) == [
            (f"group-1-{second_draft_id.replace('-', '')[:8]}", "Grupp 1", 0),
        ]
        owner_statuses = await get_owner_draft_statuses(owner_id)
        assert owner_statuses.count("active") == 1
        assert "superseded" in owner_statuses

        run_alembic_cmd(command.upgrade, "head")
        assert backfilled_groups == await get_backfilled_group_rows(draft_id)

        async with engine.connect() as conn:
            snapshot_tables = await conn.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM classroom_planner_arrangement_snapshots
                    WHERE owner_user_id = :owner_user_id
                    """
                ),
                {"owner_user_id": owner_id},
            )
            assert snapshot_tables.scalar_one() == 0

        run_alembic_cmd(command.downgrade, base_revision)
        tables_after_downgrade = await get_tables()
        assert "classroom_planner_rosters" not in tables_after_downgrade
        assert "classroom_planner_room_templates" not in tables_after_downgrade
        assert "classroom_planner_plan_drafts" not in tables_after_downgrade
        assert "classroom_planner_arrangement_snapshots" not in tables_after_downgrade

        run_alembic_cmd(command.upgrade, target_revision)
        tables_after_reupgrade = await get_tables()
        assert "classroom_planner_draft_groups" in tables_after_reupgrade
        assert "classroom_planner_arrangement_snapshots" in tables_after_reupgrade
        assert "fixtures" in await get_columns("classroom_planner_room_templates")
    finally:
        await engine.dispose()
