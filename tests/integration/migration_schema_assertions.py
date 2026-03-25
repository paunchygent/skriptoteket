"""Schema assertions for revision-focused Alembic idempotency tests.

This module centralizes the uncovered migration revisions that still need
explicit integration coverage and provides behavior-level schema assertions for
each revision. The companion idempotency runner upgrades to a revision, reruns
that same revision as a no-op, downgrades to its parent, and upgrades again.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

RevisionAssertion = Callable[[AsyncEngine], Awaitable[None]]

COVERED_REVISION_IDS: tuple[str, ...] = (
    "0001_init",
    "0012_tool_owner_user_id",
    "0014_tool_versions_settings",
    "0022_email_verification_tokens",
    "0026_profile_ai_settings",
    "0032_user_file_vault",
    "57a6ea32ef0a",
    "f30ac060991c",
    "4f5605f8be18",
    "8a1d4c7b32ef",
    "c2a6b2f4d91e",
    "d8f0d0ef2b6d",
    "9f1a6c4d2e7b",
    "6b44e9b5d3c1",
    "91f6c4a7b2d1",
    "4cb43fe0cf54",
    "71e8b6f24c1a",
    "9d7c4a12b6ef",
    "b18f6a0d3e2c",
    "c9c1c9270a3d",
    "e4b7c2d9a1f0",
    "4a9d7c1e2b34",
)


async def _table_names(engine: AsyncEngine) -> set[str]:
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        )
        return {row[0] for row in result.fetchall()}


async def _column_map(engine: AsyncEngine, table_name: str) -> dict[str, dict[str, object]]:
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


async def _index_names(engine: AsyncEngine, table_name: str) -> set[str]:
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


async def _check_constraint_names(engine: AsyncEngine, table_name: str) -> set[str]:
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


async def _scalar_count(engine: AsyncEngine, table_name: str) -> int:
    async with engine.connect() as conn:
        result = await conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
        return int(result.scalar_one())


async def _assert_0001_init(engine: AsyncEngine) -> None:
    tables = await _table_names(engine)
    assert {"users", "sessions"}.issubset(tables)
    assert "ix_users_email" in await _index_names(engine, "users")
    assert "ix_users_external_id" in await _index_names(engine, "users")
    assert "ix_sessions_user_id" in await _index_names(engine, "sessions")
    assert "ix_sessions_expires_at" in await _index_names(engine, "sessions")


async def _assert_0012_tool_owner_user_id(engine: AsyncEngine) -> None:
    columns = await _column_map(engine, "tools")
    assert "owner_user_id" in columns
    assert columns["owner_user_id"]["is_nullable"] == "NO"
    assert "ix_tools_owner_user_id" in await _index_names(engine, "tools")


async def _assert_0014_tool_versions_settings(engine: AsyncEngine) -> None:
    assert "settings_schema" in await _column_map(engine, "tool_versions")


async def _assert_0022_email_verification_tokens(engine: AsyncEngine) -> None:
    tables = await _table_names(engine)
    assert "email_verification_tokens" in tables
    indexes = await _index_names(engine, "email_verification_tokens")
    assert {
        "ix_email_verification_tokens_user_id",
        "ix_email_verification_tokens_token",
        "ix_email_verification_tokens_expires_at",
    }.issubset(indexes)


async def _assert_0026_profile_ai_settings(engine: AsyncEngine) -> None:
    assert "allow_remote_fallback" in await _column_map(engine, "user_profiles")


async def _assert_0032_user_file_vault(engine: AsyncEngine) -> None:
    tables = await _table_names(engine)
    assert {"user_vault_files", "user_vault_usage"}.issubset(tables)
    indexes = await _index_names(engine, "user_vault_files")
    assert {
        "ix_user_vault_files_user_id",
        "ix_user_vault_files_deleted_at",
        "ix_user_vault_files_source_run_id",
    }.issubset(indexes)


async def _assert_57a6_create_rosters_and_templates(engine: AsyncEngine) -> None:
    tables = await _table_names(engine)
    assert {"classroom_planner_rosters", "classroom_planner_room_templates"}.issubset(tables)


async def _assert_f30a_create_plan_drafts(engine: AsyncEngine) -> None:
    tables = await _table_names(engine)
    assert "classroom_planner_plan_drafts" in tables
    columns = await _column_map(engine, "classroom_planner_plan_drafts")
    assert {"roster_id", "template_id", "lesson_mode_id"}.issubset(columns)


async def _assert_4f56_refactor_assignments(engine: AsyncEngine) -> None:
    tables = await _table_names(engine)
    assert {
        "classroom_planner_group_assignments",
        "classroom_planner_seat_assignments",
    }.issubset(tables)
    columns = await _column_map(engine, "classroom_planner_plan_drafts")
    assert {"group_count", "revision"}.issubset(columns)
    assert "group_assignments" not in columns
    assert "seat_assignments" not in columns


async def _assert_8a1d_slice_two_workspace(engine: AsyncEngine) -> None:
    tables = await _table_names(engine)
    assert {
        "classroom_planner_draft_groups",
        "classroom_planner_student_planning_meta",
        "classroom_planner_pair_constraints",
        "classroom_planner_planning_profiles",
        "classroom_planner_arrangement_snapshots",
    }.issubset(tables)
    assert "fixtures" in await _column_map(engine, "classroom_planner_room_templates")
    assert "engine_metadata" in await _column_map(engine, "classroom_planner_plan_drafts")


async def _assert_c2a6_draft_lifecycle(engine: AsyncEngine) -> None:
    columns = await _column_map(engine, "classroom_planner_plan_drafts")
    assert {"status", "last_opened_at"}.issubset(columns)


async def _assert_d8f0_single_active_draft(engine: AsyncEngine) -> None:
    assert "uq_cp_active_draft_owner" in await _index_names(engine, "classroom_planner_plan_drafts")


async def _assert_9f1a_prune_superseded(engine: AsyncEngine) -> None:
    tables = await _table_names(engine)
    assert "classroom_planner_arrangement_snapshots" not in tables
    assert "classroom_planner_planning_profiles" not in tables
    assert "classroom_planner_pair_constraints" not in tables
    draft_columns = await _column_map(engine, "classroom_planner_plan_drafts")
    assert "engine_metadata" not in draft_columns
    assert "lesson_mode_id" not in draft_columns
    meta_columns = await _column_map(engine, "classroom_planner_student_planning_meta")
    assert "independent_focus_support" not in meta_columns


async def _assert_6b44_draft_kind(engine: AsyncEngine) -> None:
    columns = await _column_map(engine, "classroom_planner_plan_drafts")
    assert "draft_kind" in columns
    assert columns["template_id"]["is_nullable"] == "YES"
    assert "uq_cp_active_draft_roster_kind" in await _index_names(
        engine, "classroom_planner_plan_drafts"
    )
    assert "ck_cp_seating_draft_requires_template" in await _check_constraint_names(
        engine, "classroom_planner_plan_drafts"
    )


async def _assert_91f6_roomless_seating(engine: AsyncEngine) -> None:
    assert "ck_cp_seating_draft_requires_template" not in await _check_constraint_names(
        engine, "classroom_planner_plan_drafts"
    )


async def _assert_4cb4_grouping_history(engine: AsyncEngine) -> None:
    columns = await _column_map(engine, "classroom_planner_plan_drafts")
    assert {"history_stack", "undo_index"}.issubset(columns)


async def _assert_71e8_group_name_custom_flag(engine: AsyncEngine) -> None:
    assert "name_is_custom" in await _column_map(engine, "classroom_planner_draft_groups")


async def _assert_9d7c_room_template_grid_dimensions(engine: AsyncEngine) -> None:
    columns = await _column_map(engine, "classroom_planner_room_templates")
    assert {"grid_cols", "grid_rows"}.issubset(columns)


async def _assert_b18f_seating_export_jobs(engine: AsyncEngine) -> None:
    tables = await _table_names(engine)
    assert "classroom_planner_seating_export_jobs" in tables
    columns = await _column_map(engine, "classroom_planner_seating_export_jobs")
    assert columns["layout_id"]["is_nullable"] == "NO"
    assert columns["paper_size"]["is_nullable"] == "NO"
    indexes = await _index_names(engine, "classroom_planner_seating_export_jobs")
    assert {
        "ix_cp_seating_export_jobs_owner_created",
        "ix_cp_seating_export_jobs_owner_user_id",
        "ix_cp_seating_export_jobs_draft_id",
        "ix_cp_seating_export_jobs_status",
        "uq_cp_seating_export_jobs_upstream",
    }.issubset(indexes)


async def _assert_c9c1_shared_export_binding(engine: AsyncEngine) -> None:
    tables = await _table_names(engine)
    assert "classroom_planner_seating_export_webhook_bindings" in tables
    assert await _scalar_count(engine, "classroom_planner_seating_export_webhook_bindings") == 1


async def _assert_e4b7_smart_enabled(engine: AsyncEngine) -> None:
    assert "smart_enabled" in await _column_map(engine, "classroom_planner_plan_drafts")


async def _assert_4a9d_nullable_xlsx_fields(engine: AsyncEngine) -> None:
    columns = await _column_map(engine, "classroom_planner_seating_export_jobs")
    assert columns["layout_id"]["is_nullable"] == "YES"
    assert columns["paper_size"]["is_nullable"] == "YES"


SCHEMA_ASSERTIONS: dict[str, RevisionAssertion] = {
    "0001_init": _assert_0001_init,
    "0012_tool_owner_user_id": _assert_0012_tool_owner_user_id,
    "0014_tool_versions_settings": _assert_0014_tool_versions_settings,
    "0022_email_verification_tokens": _assert_0022_email_verification_tokens,
    "0026_profile_ai_settings": _assert_0026_profile_ai_settings,
    "0032_user_file_vault": _assert_0032_user_file_vault,
    "57a6ea32ef0a": _assert_57a6_create_rosters_and_templates,
    "f30ac060991c": _assert_f30a_create_plan_drafts,
    "4f5605f8be18": _assert_4f56_refactor_assignments,
    "8a1d4c7b32ef": _assert_8a1d_slice_two_workspace,
    "c2a6b2f4d91e": _assert_c2a6_draft_lifecycle,
    "d8f0d0ef2b6d": _assert_d8f0_single_active_draft,
    "9f1a6c4d2e7b": _assert_9f1a_prune_superseded,
    "6b44e9b5d3c1": _assert_6b44_draft_kind,
    "91f6c4a7b2d1": _assert_91f6_roomless_seating,
    "4cb43fe0cf54": _assert_4cb4_grouping_history,
    "71e8b6f24c1a": _assert_71e8_group_name_custom_flag,
    "9d7c4a12b6ef": _assert_9d7c_room_template_grid_dimensions,
    "b18f6a0d3e2c": _assert_b18f_seating_export_jobs,
    "c9c1c9270a3d": _assert_c9c1_shared_export_binding,
    "e4b7c2d9a1f0": _assert_e4b7_smart_enabled,
    "4a9d7c1e2b34": _assert_4a9d_nullable_xlsx_fields,
}


async def assert_schema_for_revision(revision_id: str, engine: AsyncEngine) -> None:
    """Run the registered schema assertion for a covered revision."""
    await SCHEMA_ASSERTIONS[revision_id](engine)
