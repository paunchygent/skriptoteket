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
    "f6c1e2a9b3d4",
    "7b8a6f1d2c3e",
    "8c4d2e1f7a9b",
    "1d3e5f7a9b2c",
    "5f2c7d1a9b8e",
    "4a9d7c1e2b34",
    "2b6c4d8e1f9a",
    "6a1e9d3c4b7f",
    "7d4c1a2b9e6f",
    "3e8b5c1a7d4f",
    "4d2c6b8e1a9f",
    "8f3d2c1b4a6e",
    "a1e4d6c8b2f0",
    "b7f9c2d4e1a6",
    "d3a9f6b2c4e7",
    "c1d2e3f4a5b6",
    "a8f5c7d9e2b1",
    "b4c6d8e1f2a3",
    "c7d9e3f5a1b2",
    "e2f4a6b8c9d0",
    "f8a2c6d4e9b1",
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


async def _index_definitions(engine: AsyncEngine, table_name: str) -> dict[str, str]:
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


async def _foreign_key_targets(engine: AsyncEngine, table_name: str) -> dict[str, str]:
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                """
                SELECT
                    kcu.column_name,
                    ccu.table_name
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


async def _foreign_key_delete_rules(engine: AsyncEngine, table_name: str) -> dict[str, str]:
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                """
                SELECT
                    kcu.column_name,
                    rc.delete_rule
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


async def _assert_8f3d_password_reset_tokens(engine: AsyncEngine) -> None:
    tables = await _table_names(engine)
    assert "password_reset_tokens" in tables
    indexes = await _index_names(engine, "password_reset_tokens")
    assert {
        "ix_password_reset_tokens_user_id",
        "ix_password_reset_tokens_token_hash",
        "ix_password_reset_tokens_expires_at",
    }.issubset(indexes)
    columns = await _column_map(engine, "password_reset_tokens")
    assert {"user_id", "token_hash", "expires_at", "used_at", "created_at"}.issubset(columns)


async def _assert_a1e4_default_klassrumskartan_favorite(engine: AsyncEngine) -> None:
    await _assert_8f3d_password_reset_tokens(engine)
    tables = await _table_names(engine)
    assert "user_favorite_apps" in tables


async def _assert_b7f9_drop_legacy_student_notes(engine: AsyncEngine) -> None:
    await _assert_a1e4_default_klassrumskartan_favorite(engine)
    tables = await _table_names(engine)
    assert "classroom_planner_student_planning_meta" not in tables


async def _assert_d3a9_guest_upgrade_identity(engine: AsyncEngine) -> None:
    await _assert_b7f9_drop_legacy_student_notes(engine)
    columns = await _column_map(engine, "classroom_planner_plan_drafts")
    assert {
        "task_entry_classroom_selection_mode",
        "guest_import_identity",
    }.issubset(columns)
    indexes = await _index_names(engine, "classroom_planner_plan_drafts")
    assert "uq_cp_guest_import_identity" in indexes


async def _assert_c1d2_drop_browser_auth_sessions(engine: AsyncEngine) -> None:
    await _assert_d3a9_guest_upgrade_identity(engine)
    tables = await _table_names(engine)
    assert "sessions" not in tables
    assert "tool_sessions" in tables


async def _assert_a8f5_classroom_planner_share_artifacts(engine: AsyncEngine) -> None:
    await _assert_c1d2_drop_browser_auth_sessions(engine)
    tables = await _table_names(engine)
    assert "classroom_planner_share_artifacts" in tables
    columns = await _column_map(engine, "classroom_planner_share_artifacts")
    assert {
        "token_hash",
        "source",
        "draft_kind",
        "owner_user_id",
        "draft_id",
        "roster_id",
        "template_id",
        "source_revision",
        "renderer_version",
        "presentation_schema_version",
        "presentation_hash",
        "content_hash",
        "presentation_payload",
        "rendered_html",
        "rendered_css",
        "revoked_at",
        "expires_at",
    }.issubset(columns)
    assert columns["token_hash"]["is_nullable"] == "NO"
    assert columns["rendered_html"]["is_nullable"] == "NO"
    assert columns["rendered_css"]["is_nullable"] == "NO"
    indexes = await _index_names(engine, "classroom_planner_share_artifacts")
    assert {
        "ix_classroom_planner_share_artifacts_token_hash",
        "ix_classroom_planner_share_artifacts_source",
        "ix_classroom_planner_share_artifacts_owner_user_id",
        "ix_classroom_planner_share_artifacts_draft_id",
        "ix_cp_share_artifacts_owner_draft_kind_created",
        "ix_cp_share_artifacts_expires_at",
        "ix_cp_share_artifacts_revoked_at",
    }.issubset(indexes)
    foreign_keys = await _foreign_key_targets(engine, "classroom_planner_share_artifacts")
    assert foreign_keys["owner_user_id"] == "users"
    assert foreign_keys["draft_id"] == "classroom_planner_plan_drafts"


async def _assert_b4c6_share_artifact_lifecycle_fks(engine: AsyncEngine) -> None:
    await _assert_a8f5_classroom_planner_share_artifacts(engine)
    delete_rules = await _foreign_key_delete_rules(
        engine,
        "classroom_planner_share_artifacts",
    )
    assert delete_rules["owner_user_id"] == "NO ACTION"
    assert delete_rules["draft_id"] == "NO ACTION"


async def _assert_c7d9_share_artifact_public_path(engine: AsyncEngine) -> None:
    await _assert_b4c6_share_artifact_lifecycle_fks(engine)
    columns = await _column_map(engine, "classroom_planner_share_artifacts")
    assert "public_path" in columns
    assert columns["public_path"]["is_nullable"] == "YES"


async def _assert_e2f4_public_guest_share_controls(engine: AsyncEngine) -> None:
    await _assert_c7d9_share_artifact_public_path(engine)
    columns = await _column_map(engine, "classroom_planner_share_artifacts")
    assert {
        "guest_snapshot_fingerprint",
        "client_operation_id",
        "revoke_secret_hash",
    }.issubset(columns)
    assert columns["guest_snapshot_fingerprint"]["is_nullable"] == "YES"
    assert columns["client_operation_id"]["is_nullable"] == "YES"
    assert columns["revoke_secret_hash"]["is_nullable"] == "YES"
    indexes = await _index_names(engine, "classroom_planner_share_artifacts")
    assert {
        "ix_cp_share_artifacts_public_client_op",
        "ix_cp_share_artifacts_guest_fingerprint",
    }.issubset(indexes)


async def _assert_f8a2_share_preview_assets(engine: AsyncEngine) -> None:
    await _assert_e2f4_public_guest_share_controls(engine)
    tables = await _table_names(engine)
    assert "classroom_planner_share_preview_assets" in tables
    columns = await _column_map(engine, "classroom_planner_share_preview_assets")
    assert {
        "share_id",
        "content_type",
        "width",
        "height",
        "image_bytes",
        "preview_content_hash",
        "source_content_hash",
        "presentation_hash",
        "renderer_version",
        "generated_at",
        "updated_at",
    }.issubset(columns)
    assert columns["share_id"]["is_nullable"] == "NO"
    assert columns["image_bytes"]["is_nullable"] == "NO"
    foreign_keys = await _foreign_key_targets(engine, "classroom_planner_share_preview_assets")
    assert foreign_keys["share_id"] == "classroom_planner_share_artifacts"
    delete_rules = await _foreign_key_delete_rules(
        engine,
        "classroom_planner_share_preview_assets",
    )
    assert delete_rules["share_id"] == "CASCADE"
    indexes = await _index_names(engine, "classroom_planner_share_preview_assets")
    assert {
        "ix_cp_share_preview_assets_source_hash",
        "ix_cp_share_preview_assets_preview_hash",
    }.issubset(indexes)


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


async def _assert_f6c1_grouping_export_jobs(engine: AsyncEngine) -> None:
    tables = await _table_names(engine)
    assert "classroom_planner_grouping_export_jobs" in tables
    columns = await _column_map(engine, "classroom_planner_grouping_export_jobs")
    assert columns["paper_size"]["is_nullable"] == "YES"
    indexes = await _index_names(engine, "classroom_planner_grouping_export_jobs")
    assert {
        "ix_cp_grouping_export_jobs_owner_created",
        "ix_classroom_planner_grouping_export_jobs_owner_user_id",
        "ix_classroom_planner_grouping_export_jobs_draft_id",
        "ix_classroom_planner_grouping_export_jobs_status",
        "uq_cp_grouping_export_jobs_upstream",
    }.issubset(indexes)


async def _assert_7b8a_planner_draft_flags(engine: AsyncEngine) -> None:
    columns = await _column_map(engine, "classroom_planner_plan_drafts")
    assert {"use_history", "grouping_seating_distance_enabled"}.issubset(columns)
    assert columns["use_history"]["is_nullable"] == "NO"
    assert columns["grouping_seating_distance_enabled"]["is_nullable"] == "NO"


async def _assert_8c4d_planner_smart_rule_tables(engine: AsyncEngine) -> None:
    tables = await _table_names(engine)
    assert {
        "classroom_planner_student_smart_preferences",
        "classroom_planner_relationship_rules",
    }.issubset(tables)
    smart_columns = await _column_map(engine, "classroom_planner_student_smart_preferences")
    assert {"draft_id", "student_id", "support_seat"}.issubset(smart_columns)
    relationship_columns = await _column_map(engine, "classroom_planner_relationship_rules")
    assert {"draft_id", "rule_id", "kind", "student_ids"}.issubset(relationship_columns)
    legacy_meta_columns = await _column_map(engine, "classroom_planner_student_planning_meta")
    assert "teacher_proximity" not in legacy_meta_columns
    assert "stability_preference" not in legacy_meta_columns
    assert "preferred_zone" not in legacy_meta_columns
    assert "avoid_zone" not in legacy_meta_columns


async def _assert_1d3e_seating_preferences_reset(engine: AsyncEngine) -> None:
    tables = await _table_names(engine)
    assert "classroom_planner_student_seating_preferences" in tables
    assert "classroom_planner_student_smart_preferences" not in tables
    seating_columns = await _column_map(engine, "classroom_planner_student_seating_preferences")
    assert {"draft_id", "student_id", "near_teacher"}.issubset(seating_columns)
    relationship_columns = await _column_map(engine, "classroom_planner_relationship_rules")
    assert {"draft_id", "rule_id", "kind", "student_ids"}.issubset(relationship_columns)


async def _assert_4a9d_nullable_xlsx_fields(engine: AsyncEngine) -> None:
    columns = await _column_map(engine, "classroom_planner_seating_export_jobs")
    assert columns["layout_id"]["is_nullable"] == "YES"
    assert columns["paper_size"]["is_nullable"] == "YES"


async def _assert_5f2c_roster_owned_smart_rules(engine: AsyncEngine) -> None:
    tables = await _table_names(engine)
    assert "classroom_planner_roster_smart_rule_sets" in tables
    assert "classroom_planner_roster_seating_preferences" in tables
    assert "classroom_planner_roster_relationship_rules" in tables
    assert "classroom_planner_student_seating_preferences" not in tables
    assert "classroom_planner_relationship_rules" not in tables
    root_columns = await _column_map(engine, "classroom_planner_roster_smart_rule_sets")
    assert {"roster_id", "revision", "updated_at"}.issubset(root_columns)
    seating_columns = await _column_map(engine, "classroom_planner_roster_seating_preferences")
    assert {"roster_id", "student_id", "near_teacher"}.issubset(seating_columns)
    relationship_columns = await _column_map(engine, "classroom_planner_roster_relationship_rules")
    assert {"roster_id", "rule_id", "kind", "student_ids"}.issubset(relationship_columns)
    seating_foreign_keys = await _foreign_key_targets(
        engine, "classroom_planner_roster_seating_preferences"
    )
    assert seating_foreign_keys["roster_id"] == "classroom_planner_roster_smart_rule_sets"
    relationship_foreign_keys = await _foreign_key_targets(
        engine, "classroom_planner_roster_relationship_rules"
    )
    assert relationship_foreign_keys["roster_id"] == "classroom_planner_roster_smart_rule_sets"


async def _assert_2b6c_conversion_hub_jobs(engine: AsyncEngine) -> None:
    tables = await _table_names(engine)
    assert "conversion_hub_jobs" in tables
    columns = await _column_map(engine, "conversion_hub_jobs")
    assert {"owner_user_id", "input_filename", "source_format", "output_format"}.issubset(columns)
    assert columns["pdf_paper_size"]["is_nullable"] == "YES"
    assert columns["upstream_job_id"]["is_nullable"] == "YES"
    indexes = await _index_names(engine, "conversion_hub_jobs")
    assert {
        "ix_conversion_hub_jobs_owner_user_id",
        "ix_conversion_hub_jobs_status",
        "ix_conversion_hub_jobs_owner_created",
        "uq_conversion_hub_jobs_upstream",
    }.issubset(indexes)


async def _assert_6a1e_merged_heads(engine: AsyncEngine) -> None:
    await _assert_5f2c_roster_owned_smart_rules(engine)
    await _assert_2b6c_conversion_hub_jobs(engine)


async def _assert_7d4c_roster_smart_rule_repair(engine: AsyncEngine) -> None:
    await _assert_6a1e_merged_heads(engine)


async def _assert_3e8b_seating_export_checkpoints(engine: AsyncEngine) -> None:
    await _assert_7d4c_roster_smart_rule_repair(engine)
    tables = await _table_names(engine)
    assert "classroom_planner_seating_export_checkpoints" in tables
    columns = await _column_map(engine, "classroom_planner_seating_export_checkpoints")
    assert {
        "roster_id",
        "template_id",
        "source_draft_id",
        "source_export_job_id",
        "room_context_hash",
        "assignment_hash",
        "room_context",
        "seating_snapshot",
    }.issubset(columns)
    indexes = await _index_names(engine, "classroom_planner_seating_export_checkpoints")
    assert {
        "ix_classroom_planner_seating_export_checkpoints_roster_id",
        "ix_classroom_planner_seating_export_checkpoints_source_draft_id",
        "ix_classroom_planner_seating_export_checkpoints_template_id",
        "ix_cp_seating_export_checkpoints_roster_room_created",
        "uq_cp_seating_export_checkpoints_source_job",
    }.issubset(indexes)
    foreign_keys = await _foreign_key_targets(
        engine,
        "classroom_planner_seating_export_checkpoints",
    )
    assert foreign_keys["roster_id"] == "classroom_planner_rosters"
    assert foreign_keys["template_id"] == "classroom_planner_room_templates"
    assert foreign_keys["source_draft_id"] == "classroom_planner_plan_drafts"
    assert foreign_keys["source_export_job_id"] == "classroom_planner_seating_export_jobs"


async def _assert_4d2c_grouping_export_checkpoints(engine: AsyncEngine) -> None:
    await _assert_3e8b_seating_export_checkpoints(engine)
    tables = await _table_names(engine)
    assert "classroom_planner_grouping_export_checkpoints" in tables
    columns = await _column_map(engine, "classroom_planner_grouping_export_checkpoints")
    assert {
        "roster_id",
        "template_id",
        "source_draft_id",
        "source_export_job_id",
        "assignment_hash",
        "grouping_snapshot",
    }.issubset(columns)
    indexes = await _index_names(engine, "classroom_planner_grouping_export_checkpoints")
    assert {
        "ix_classroom_planner_grouping_export_checkpoints_roster_id",
        "ix_classroom_planner_grouping_export_checkpoints_template_id",
        "ix_cp_grouping_export_checkpoints_roster_created",
        "uq_cp_grouping_export_checkpoints_source_job",
    }.issubset(indexes)
    index_definitions = await _index_definitions(
        engine, "classroom_planner_grouping_export_checkpoints"
    )
    assert any(
        name.startswith("ix_classroom_planner_grouping_export_checkpoints_source_")
        and "(source_draft_id)" in definition
        for name, definition in index_definitions.items()
    )
    foreign_keys = await _foreign_key_targets(
        engine,
        "classroom_planner_grouping_export_checkpoints",
    )
    assert foreign_keys["roster_id"] == "classroom_planner_rosters"
    assert foreign_keys["template_id"] == "classroom_planner_room_templates"
    assert foreign_keys["source_draft_id"] == "classroom_planner_plan_drafts"
    assert foreign_keys["source_export_job_id"] == "classroom_planner_grouping_export_jobs"


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
    "f6c1e2a9b3d4": _assert_f6c1_grouping_export_jobs,
    "7b8a6f1d2c3e": _assert_7b8a_planner_draft_flags,
    "8c4d2e1f7a9b": _assert_8c4d_planner_smart_rule_tables,
    "1d3e5f7a9b2c": _assert_1d3e_seating_preferences_reset,
    "5f2c7d1a9b8e": _assert_5f2c_roster_owned_smart_rules,
    "4a9d7c1e2b34": _assert_4a9d_nullable_xlsx_fields,
    "2b6c4d8e1f9a": _assert_2b6c_conversion_hub_jobs,
    "6a1e9d3c4b7f": _assert_6a1e_merged_heads,
    "7d4c1a2b9e6f": _assert_7d4c_roster_smart_rule_repair,
    "3e8b5c1a7d4f": _assert_3e8b_seating_export_checkpoints,
    "4d2c6b8e1a9f": _assert_4d2c_grouping_export_checkpoints,
    "8f3d2c1b4a6e": _assert_8f3d_password_reset_tokens,
    "a1e4d6c8b2f0": _assert_a1e4_default_klassrumskartan_favorite,
    "b7f9c2d4e1a6": _assert_b7f9_drop_legacy_student_notes,
    "d3a9f6b2c4e7": _assert_d3a9_guest_upgrade_identity,
    "c1d2e3f4a5b6": _assert_c1d2_drop_browser_auth_sessions,
    "a8f5c7d9e2b1": _assert_a8f5_classroom_planner_share_artifacts,
    "b4c6d8e1f2a3": _assert_b4c6_share_artifact_lifecycle_fks,
    "c7d9e3f5a1b2": _assert_c7d9_share_artifact_public_path,
    "e2f4a6b8c9d0": _assert_e2f4_public_guest_share_controls,
    "f8a2c6d4e9b1": _assert_f8a2_share_preview_assets,
}


async def assert_schema_for_revision(revision_id: str, engine: AsyncEngine) -> None:
    """Run the registered schema assertion for a covered revision."""
    await SCHEMA_ASSERTIONS[revision_id](engine)
