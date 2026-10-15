"""Klassrumskartan export-checkpoint migration schema assertions.

Purpose:
    Verify export-checkpoint tables and share-checkpoint provenance during
    idempotent Alembic tests.

Relationships:
    - Registered by `migration_schema_assertions`.
    - Builds on planner assertions and shared share-artifact assertions.
    - Uses shared information-schema helpers from `migration_schema_helpers`.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine

from tests.integration.migration_schema_helpers import (
    check_constraint_names,
    column_map,
    foreign_key_targets,
    index_definitions,
    index_names,
    table_names,
)
from tests.integration.migration_schema_planner_assertions import (
    assert_7d4c_roster_smart_rule_repair,
)
from tests.integration.migration_schema_share_assertions import (
    assert_8a6d_grouping_seating_distance_default_on,
)


async def assert_3e8b_seating_export_checkpoints(engine: AsyncEngine) -> None:
    await assert_7d4c_roster_smart_rule_repair(engine)
    tables = await table_names(engine)
    assert "classroom_planner_seating_export_checkpoints" in tables
    columns = await column_map(engine, "classroom_planner_seating_export_checkpoints")
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
    indexes = await index_names(engine, "classroom_planner_seating_export_checkpoints")
    assert {
        "ix_classroom_planner_seating_export_checkpoints_roster_id",
        "ix_classroom_planner_seating_export_checkpoints_source_draft_id",
        "ix_classroom_planner_seating_export_checkpoints_template_id",
        "ix_cp_seating_export_checkpoints_roster_room_created",
        "uq_cp_seating_export_checkpoints_source_job",
    }.issubset(indexes)
    foreign_keys = await foreign_key_targets(
        engine,
        "classroom_planner_seating_export_checkpoints",
    )
    assert foreign_keys["roster_id"] == "classroom_planner_rosters"
    assert foreign_keys["template_id"] == "classroom_planner_room_templates"
    assert foreign_keys["source_draft_id"] == "classroom_planner_plan_drafts"
    assert foreign_keys["source_export_job_id"] == "classroom_planner_seating_export_jobs"


async def assert_4d2c_grouping_export_checkpoints(engine: AsyncEngine) -> None:
    await assert_3e8b_seating_export_checkpoints(engine)
    tables = await table_names(engine)
    assert "classroom_planner_grouping_export_checkpoints" in tables
    columns = await column_map(engine, "classroom_planner_grouping_export_checkpoints")
    assert {
        "roster_id",
        "template_id",
        "source_draft_id",
        "source_export_job_id",
        "assignment_hash",
        "grouping_snapshot",
    }.issubset(columns)
    indexes = await index_names(engine, "classroom_planner_grouping_export_checkpoints")
    assert {
        "ix_classroom_planner_grouping_export_checkpoints_roster_id",
        "ix_classroom_planner_grouping_export_checkpoints_template_id",
        "ix_cp_grouping_export_checkpoints_roster_created",
        "uq_cp_grouping_export_checkpoints_source_job",
    }.issubset(indexes)
    definitions = await index_definitions(engine, "classroom_planner_grouping_export_checkpoints")
    assert any(
        name.startswith("ix_classroom_planner_grouping_export_checkpoints_source_")
        and "(source_draft_id)" in definition
        for name, definition in definitions.items()
    )
    foreign_keys = await foreign_key_targets(
        engine,
        "classroom_planner_grouping_export_checkpoints",
    )
    assert foreign_keys["roster_id"] == "classroom_planner_rosters"
    assert foreign_keys["template_id"] == "classroom_planner_room_templates"
    assert foreign_keys["source_draft_id"] == "classroom_planner_plan_drafts"
    assert foreign_keys["source_export_job_id"] == "classroom_planner_grouping_export_jobs"


async def assert_f2a7_share_checkpoint_provenance(engine: AsyncEngine) -> None:
    await assert_8a6d_grouping_seating_distance_default_on(engine)
    for table_name, source_job_table, source_share_index, kind_check, source_check in (
        (
            "classroom_planner_seating_export_checkpoints",
            "classroom_planner_seating_export_jobs",
            "uq_cp_seating_export_checkpoints_source_share",
            "ck_cp_seating_export_checkpoints_source_kind",
            "ck_cp_seating_export_checkpoints_one_source",
        ),
        (
            "classroom_planner_grouping_export_checkpoints",
            "classroom_planner_grouping_export_jobs",
            "uq_cp_grouping_export_checkpoints_source_share",
            "ck_cp_grouping_export_checkpoints_source_kind",
            "ck_cp_grouping_export_checkpoints_one_source",
        ),
    ):
        columns = await column_map(engine, table_name)
        assert {"source_kind", "source_share_artifact_id"}.issubset(columns)
        assert columns["source_kind"]["is_nullable"] == "NO"
        assert columns["source_export_job_id"]["is_nullable"] == "YES"

        indexes = await index_names(engine, table_name)
        assert source_share_index in indexes

        foreign_keys = await foreign_key_targets(engine, table_name)
        assert foreign_keys["source_export_job_id"] == source_job_table
        assert foreign_keys["source_share_artifact_id"] == "classroom_planner_share_artifacts"

        constraints = await check_constraint_names(engine, table_name)
        assert {kind_check, source_check}.issubset(constraints)
