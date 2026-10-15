"""Klassrumskartan planner migration schema assertions.

Purpose:
    Verify Klassrumskartan roster, draft, workspace, smart-rule, and export-job
    schema revisions during idempotent Alembic tests.

Relationships:
    - Registered by `migration_schema_assertions`.
    - Reuses the conversion-hub job assertion for the merged-head revision.
    - Uses shared information-schema helpers from `migration_schema_helpers`.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine

from tests.integration.migration_schema_conversion_assertions import (
    assert_2b6c_conversion_hub_jobs,
)
from tests.integration.migration_schema_helpers import (
    check_constraint_names,
    column_map,
    foreign_key_targets,
    index_names,
    scalar_count,
    table_names,
)


async def assert_57a6_create_rosters_and_templates(engine: AsyncEngine) -> None:
    tables = await table_names(engine)
    assert {"classroom_planner_rosters", "classroom_planner_room_templates"}.issubset(tables)


async def assert_f30a_create_plan_drafts(engine: AsyncEngine) -> None:
    tables = await table_names(engine)
    assert "classroom_planner_plan_drafts" in tables
    columns = await column_map(engine, "classroom_planner_plan_drafts")
    assert {"roster_id", "template_id", "lesson_mode_id"}.issubset(columns)


async def assert_4f56_refactor_assignments(engine: AsyncEngine) -> None:
    tables = await table_names(engine)
    assert {
        "classroom_planner_group_assignments",
        "classroom_planner_seat_assignments",
    }.issubset(tables)
    columns = await column_map(engine, "classroom_planner_plan_drafts")
    assert {"group_count", "revision"}.issubset(columns)
    assert "group_assignments" not in columns
    assert "seat_assignments" not in columns


async def assert_8a1d_slice_two_workspace(engine: AsyncEngine) -> None:
    tables = await table_names(engine)
    assert {
        "classroom_planner_draft_groups",
        "classroom_planner_student_planning_meta",
        "classroom_planner_pair_constraints",
        "classroom_planner_planning_profiles",
        "classroom_planner_arrangement_snapshots",
    }.issubset(tables)
    assert "fixtures" in await column_map(engine, "classroom_planner_room_templates")
    assert "engine_metadata" in await column_map(engine, "classroom_planner_plan_drafts")


async def assert_c2a6_draft_lifecycle(engine: AsyncEngine) -> None:
    columns = await column_map(engine, "classroom_planner_plan_drafts")
    assert {"status", "last_opened_at"}.issubset(columns)


async def assert_d8f0_single_active_draft(engine: AsyncEngine) -> None:
    assert "uq_cp_active_draft_owner" in await index_names(engine, "classroom_planner_plan_drafts")


async def assert_9f1a_prune_superseded(engine: AsyncEngine) -> None:
    tables = await table_names(engine)
    assert "classroom_planner_arrangement_snapshots" not in tables
    assert "classroom_planner_planning_profiles" not in tables
    assert "classroom_planner_pair_constraints" not in tables
    draft_columns = await column_map(engine, "classroom_planner_plan_drafts")
    assert "engine_metadata" not in draft_columns
    assert "lesson_mode_id" not in draft_columns
    meta_columns = await column_map(engine, "classroom_planner_student_planning_meta")
    assert "independent_focus_support" not in meta_columns


async def assert_6b44_draft_kind(engine: AsyncEngine) -> None:
    columns = await column_map(engine, "classroom_planner_plan_drafts")
    assert "draft_kind" in columns
    assert columns["template_id"]["is_nullable"] == "YES"
    assert "uq_cp_active_draft_roster_kind" in await index_names(
        engine, "classroom_planner_plan_drafts"
    )
    assert "ck_cp_seating_draft_requires_template" in await check_constraint_names(
        engine, "classroom_planner_plan_drafts"
    )


async def assert_91f6_roomless_seating(engine: AsyncEngine) -> None:
    assert "ck_cp_seating_draft_requires_template" not in await check_constraint_names(
        engine, "classroom_planner_plan_drafts"
    )


async def assert_4cb4_grouping_history(engine: AsyncEngine) -> None:
    columns = await column_map(engine, "classroom_planner_plan_drafts")
    assert {"history_stack", "undo_index"}.issubset(columns)


async def assert_71e8_group_name_custom_flag(engine: AsyncEngine) -> None:
    assert "name_is_custom" in await column_map(engine, "classroom_planner_draft_groups")


async def assert_9d7c_room_template_grid_dimensions(engine: AsyncEngine) -> None:
    columns = await column_map(engine, "classroom_planner_room_templates")
    assert {"grid_cols", "grid_rows"}.issubset(columns)


async def assert_b18f_seating_export_jobs(engine: AsyncEngine) -> None:
    tables = await table_names(engine)
    assert "classroom_planner_seating_export_jobs" in tables
    columns = await column_map(engine, "classroom_planner_seating_export_jobs")
    assert columns["layout_id"]["is_nullable"] == "NO"
    assert columns["paper_size"]["is_nullable"] == "NO"
    indexes = await index_names(engine, "classroom_planner_seating_export_jobs")
    assert {
        "ix_cp_seating_export_jobs_owner_created",
        "ix_cp_seating_export_jobs_owner_user_id",
        "ix_cp_seating_export_jobs_draft_id",
        "ix_cp_seating_export_jobs_status",
        "uq_cp_seating_export_jobs_upstream",
    }.issubset(indexes)


async def assert_c9c1_shared_export_binding(engine: AsyncEngine) -> None:
    tables = await table_names(engine)
    assert "classroom_planner_seating_export_webhook_bindings" in tables
    assert await scalar_count(engine, "classroom_planner_seating_export_webhook_bindings") == 1


async def assert_e4b7_smart_enabled(engine: AsyncEngine) -> None:
    assert "smart_enabled" in await column_map(engine, "classroom_planner_plan_drafts")


async def assert_f6c1_grouping_export_jobs(engine: AsyncEngine) -> None:
    tables = await table_names(engine)
    assert "classroom_planner_grouping_export_jobs" in tables
    columns = await column_map(engine, "classroom_planner_grouping_export_jobs")
    assert columns["paper_size"]["is_nullable"] == "YES"
    indexes = await index_names(engine, "classroom_planner_grouping_export_jobs")
    assert {
        "ix_cp_grouping_export_jobs_owner_created",
        "ix_classroom_planner_grouping_export_jobs_owner_user_id",
        "ix_classroom_planner_grouping_export_jobs_draft_id",
        "ix_classroom_planner_grouping_export_jobs_status",
        "uq_cp_grouping_export_jobs_upstream",
    }.issubset(indexes)


async def assert_7b8a_planner_draft_flags(engine: AsyncEngine) -> None:
    columns = await column_map(engine, "classroom_planner_plan_drafts")
    assert {"use_history", "grouping_seating_distance_enabled"}.issubset(columns)
    assert columns["use_history"]["is_nullable"] == "NO"
    assert columns["grouping_seating_distance_enabled"]["is_nullable"] == "NO"


async def assert_8c4d_planner_smart_rule_tables(engine: AsyncEngine) -> None:
    tables = await table_names(engine)
    assert {
        "classroom_planner_student_smart_preferences",
        "classroom_planner_relationship_rules",
    }.issubset(tables)
    smart_columns = await column_map(engine, "classroom_planner_student_smart_preferences")
    assert {"draft_id", "student_id", "support_seat"}.issubset(smart_columns)
    relationship_columns = await column_map(engine, "classroom_planner_relationship_rules")
    assert {"draft_id", "rule_id", "kind", "student_ids"}.issubset(relationship_columns)
    legacy_meta_columns = await column_map(engine, "classroom_planner_student_planning_meta")
    assert "teacher_proximity" not in legacy_meta_columns
    assert "stability_preference" not in legacy_meta_columns
    assert "preferred_zone" not in legacy_meta_columns
    assert "avoid_zone" not in legacy_meta_columns


async def assert_1d3e_seating_preferences_reset(engine: AsyncEngine) -> None:
    tables = await table_names(engine)
    assert "classroom_planner_student_seating_preferences" in tables
    assert "classroom_planner_student_smart_preferences" not in tables
    seating_columns = await column_map(engine, "classroom_planner_student_seating_preferences")
    assert {"draft_id", "student_id", "near_teacher"}.issubset(seating_columns)
    relationship_columns = await column_map(engine, "classroom_planner_relationship_rules")
    assert {"draft_id", "rule_id", "kind", "student_ids"}.issubset(relationship_columns)


async def assert_4a9d_nullable_xlsx_fields(engine: AsyncEngine) -> None:
    columns = await column_map(engine, "classroom_planner_seating_export_jobs")
    assert columns["layout_id"]["is_nullable"] == "YES"
    assert columns["paper_size"]["is_nullable"] == "YES"


async def assert_5f2c_roster_owned_smart_rules(engine: AsyncEngine) -> None:
    tables = await table_names(engine)
    assert "classroom_planner_roster_smart_rule_sets" in tables
    assert "classroom_planner_roster_seating_preferences" in tables
    assert "classroom_planner_roster_relationship_rules" in tables
    assert "classroom_planner_student_seating_preferences" not in tables
    assert "classroom_planner_relationship_rules" not in tables
    root_columns = await column_map(engine, "classroom_planner_roster_smart_rule_sets")
    assert {"roster_id", "revision", "updated_at"}.issubset(root_columns)
    seating_columns = await column_map(engine, "classroom_planner_roster_seating_preferences")
    assert {"roster_id", "student_id", "near_teacher"}.issubset(seating_columns)
    relationship_columns = await column_map(engine, "classroom_planner_roster_relationship_rules")
    assert {"roster_id", "rule_id", "kind", "student_ids"}.issubset(relationship_columns)
    seating_foreign_keys = await foreign_key_targets(
        engine, "classroom_planner_roster_seating_preferences"
    )
    assert seating_foreign_keys["roster_id"] == "classroom_planner_roster_smart_rule_sets"
    relationship_foreign_keys = await foreign_key_targets(
        engine, "classroom_planner_roster_relationship_rules"
    )
    assert relationship_foreign_keys["roster_id"] == "classroom_planner_roster_smart_rule_sets"


async def assert_6a1e_merged_heads(engine: AsyncEngine) -> None:
    await assert_5f2c_roster_owned_smart_rules(engine)
    await assert_2b6c_conversion_hub_jobs(engine)


async def assert_7d4c_roster_smart_rule_repair(engine: AsyncEngine) -> None:
    await assert_6a1e_merged_heads(engine)
