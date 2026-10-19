"""Integration coverage for classroom planner schema migrations.

This module verifies that the Slice 2 classroom planner schema upgrades cleanly
to the latest head, tolerates a no-op re-upgrade, backfills draft groups from
the previous draft shape, and can be downgraded and upgraded again without
leaving the database in a partial state.
"""

import os

import pytest
from alembic import command
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from tests.fixtures.database_fixtures import PooledDatabase, alembic_config_for
from tests.integration.database.classroom_planner_migration_support import (
    get_backfilled_group_rows,
    get_columns,
    get_group_assignment_ids,
    get_index_names,
    get_owner_draft_statuses,
    get_tables,
    insert_active_grouping_draft,
    insert_second_roster_with_active_drafts,
    run_alembic_cmd,
    seed_pre_slice_two_draft,
)


async def _assert_schema_at_target_revision(engine: AsyncEngine) -> None:
    tables = await get_tables(engine)
    assert {
        "classroom_planner_rosters",
        "classroom_planner_room_templates",
        "classroom_planner_plan_drafts",
        "classroom_planner_share_artifacts",
        "classroom_planner_group_assignments",
        "classroom_planner_seat_assignments",
        "classroom_planner_draft_groups",
    }.issubset(tables)
    assert "classroom_planner_student_planning_meta" not in tables
    assert "classroom_planner_pair_constraints" not in tables
    assert "classroom_planner_planning_profiles" not in tables
    assert "classroom_planner_arrangement_snapshots" not in tables

    assert "fixtures" in await get_columns(engine, "classroom_planner_room_templates")
    assert "status" in await get_columns(engine, "classroom_planner_plan_drafts")
    assert "draft_kind" in await get_columns(engine, "classroom_planner_plan_drafts")
    assert "last_opened_at" in await get_columns(engine, "classroom_planner_plan_drafts")
    assert "task_entry_classroom_selection_mode" in await get_columns(
        engine, "classroom_planner_plan_drafts"
    )
    assert "guest_import_identity" in await get_columns(engine, "classroom_planner_plan_drafts")
    share_columns = await get_columns(engine, "classroom_planner_share_artifacts")
    assert {
        "token_hash",
        "source",
        "draft_kind",
        "source_revision",
        "public_path",
        "renderer_version",
        "presentation_schema_version",
        "presentation_hash",
        "content_hash",
        "presentation_payload",
        "rendered_html",
        "rendered_css",
        "revoked_at",
        "expires_at",
    }.issubset(share_columns)
    share_indexes = await get_index_names(engine, "classroom_planner_share_artifacts")
    assert "ix_classroom_planner_share_artifacts_token_hash" in share_indexes
    assert "ix_cp_share_artifacts_owner_draft_kind_created" in share_indexes
    assert "lesson_mode_id" not in await get_columns(engine, "classroom_planner_plan_drafts")
    assert "engine_metadata" not in await get_columns(engine, "classroom_planner_plan_drafts")
    assert "group_count" not in await get_columns(engine, "classroom_planner_plan_drafts")
    assert "uq_cp_active_draft_roster_kind" in await get_index_names(
        engine, "classroom_planner_plan_drafts"
    )
    assert "uq_cp_guest_import_identity" in await get_index_names(
        engine, "classroom_planner_plan_drafts"
    )
    assert "uq_cp_active_draft_owner" not in await get_index_names(
        engine, "classroom_planner_plan_drafts"
    )


async def _assert_schema_after_downgrade(engine: AsyncEngine) -> None:
    tables_after_downgrade = await get_tables(engine)
    assert "classroom_planner_rosters" not in tables_after_downgrade
    assert "classroom_planner_room_templates" not in tables_after_downgrade
    assert "classroom_planner_plan_drafts" not in tables_after_downgrade
    assert "classroom_planner_arrangement_snapshots" not in tables_after_downgrade


async def _assert_schema_after_reupgrade(engine: AsyncEngine) -> None:
    tables_after_reupgrade = await get_tables(engine)
    assert "classroom_planner_draft_groups" in tables_after_reupgrade
    assert "classroom_planner_share_artifacts" in tables_after_reupgrade
    assert "classroom_planner_student_planning_meta" not in tables_after_reupgrade
    assert "classroom_planner_arrangement_snapshots" not in tables_after_reupgrade
    assert "classroom_planner_pair_constraints" not in tables_after_reupgrade
    assert "classroom_planner_planning_profiles" not in tables_after_reupgrade
    assert "fixtures" in await get_columns(engine, "classroom_planner_room_templates")
    assert "draft_kind" in await get_columns(engine, "classroom_planner_plan_drafts")
    assert "task_entry_classroom_selection_mode" in await get_columns(
        engine, "classroom_planner_plan_drafts"
    )
    assert "guest_import_identity" in await get_columns(engine, "classroom_planner_plan_drafts")
    assert "lesson_mode_id" not in await get_columns(engine, "classroom_planner_plan_drafts")
    assert "engine_metadata" not in await get_columns(engine, "classroom_planner_plan_drafts")


@pytest.mark.integration
@pytest.mark.docker
@pytest.mark.asyncio
async def test_classroom_planner_migration_idempotency(empty_module_database: PooledDatabase):
    """Verify planner migrations reach the current head cleanly and stay re-runnable."""
    database_url = empty_module_database.url
    os.environ["DATABASE_URL"] = database_url

    alembic_cfg = alembic_config_for(database_url=database_url)

    target_revision = "f8a2c6d4e9b1"
    pre_slice_two_revision = "4f5605f8be18"
    base_revision = "0032_user_file_vault"

    engine = create_async_engine(database_url)

    try:
        run_alembic_cmd(alembic_cfg, command.upgrade, pre_slice_two_revision)
        seeded = await seed_pre_slice_two_draft(engine)
        draft_id = seeded.draft_id
        second_draft_id = seeded.second_draft_id
        owner_id = seeded.owner_id
        roster_id = seeded.roster_id

        run_alembic_cmd(alembic_cfg, command.upgrade, target_revision)

        await _assert_schema_at_target_revision(engine)

        backfilled_groups = await get_backfilled_group_rows(engine, draft_id)
        assert backfilled_groups == [
            (f"group-1-{draft_id.replace('-', '')[:8]}", "Grupp 1", 0),
            (f"group-2-{draft_id.replace('-', '')[:8]}", "Grupp 2", 1),
        ]
        assert await get_group_assignment_ids(engine, draft_id) == [
            f"group-1-{draft_id.replace('-', '')[:8]}",
            f"group-2-{draft_id.replace('-', '')[:8]}",
        ]
        assert await get_backfilled_group_rows(engine, second_draft_id) == [
            (f"group-1-{second_draft_id.replace('-', '')[:8]}", "Grupp 1", 0),
        ]
        owner_statuses = await get_owner_draft_statuses(engine, owner_id)
        assert owner_statuses.count("active") == 1
        assert "superseded" in owner_statuses

        await insert_second_roster_with_active_drafts(
            engine, owner_id=owner_id, roster_id=roster_id
        )
        with pytest.raises(Exception):
            await insert_active_grouping_draft(engine, owner_id=owner_id, roster_id=roster_id)

        run_alembic_cmd(alembic_cfg, command.upgrade, "head")
        assert backfilled_groups == await get_backfilled_group_rows(engine, draft_id)

        run_alembic_cmd(alembic_cfg, command.downgrade, base_revision)
        await _assert_schema_after_downgrade(engine)

        run_alembic_cmd(alembic_cfg, command.upgrade, target_revision)
        await _assert_schema_after_reupgrade(engine)
    finally:
        await engine.dispose()
