"""Share and fixed-seat migration schema assertions.

Purpose:
    Verify Klassrumskartan share-artifact, preview-asset, and fixed-seat
    smart-rule schema revisions during idempotent Alembic tests.

Relationships:
    - Registered by `migration_schema_assertions`.
    - Uses shared information-schema helpers from `migration_schema_helpers`.
"""

from sqlalchemy.ext.asyncio import AsyncEngine

from tests.integration.migration_schema_helpers import (
    column_defaults,
    column_map,
    foreign_key_delete_rules,
    foreign_key_targets,
    index_names,
    table_names,
)


async def assert_a8f5_classroom_planner_share_artifacts(engine: AsyncEngine) -> None:
    """Verify the authenticated share artifact table."""

    tables = await table_names(engine)
    assert "classroom_planner_share_artifacts" in tables
    columns = await column_map(engine, "classroom_planner_share_artifacts")
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
    indexes = await index_names(engine, "classroom_planner_share_artifacts")
    assert {
        "ix_classroom_planner_share_artifacts_token_hash",
        "ix_classroom_planner_share_artifacts_source",
        "ix_classroom_planner_share_artifacts_owner_user_id",
        "ix_classroom_planner_share_artifacts_draft_id",
        "ix_cp_share_artifacts_owner_draft_kind_created",
        "ix_cp_share_artifacts_expires_at",
        "ix_cp_share_artifacts_revoked_at",
    }.issubset(indexes)
    foreign_keys = await foreign_key_targets(engine, "classroom_planner_share_artifacts")
    assert foreign_keys["owner_user_id"] == "users"
    assert foreign_keys["draft_id"] == "classroom_planner_plan_drafts"


async def assert_b4c6_share_artifact_lifecycle_fks(engine: AsyncEngine) -> None:
    """Verify share artifact foreign-key lifecycle behavior."""

    await assert_a8f5_classroom_planner_share_artifacts(engine)
    delete_rules = await foreign_key_delete_rules(
        engine,
        "classroom_planner_share_artifacts",
    )
    assert delete_rules["owner_user_id"] == "NO ACTION"
    assert delete_rules["draft_id"] == "NO ACTION"


async def assert_c7d9_share_artifact_public_path(engine: AsyncEngine) -> None:
    """Verify the public share path column."""

    await assert_b4c6_share_artifact_lifecycle_fks(engine)
    columns = await column_map(engine, "classroom_planner_share_artifacts")
    assert "public_path" in columns
    assert columns["public_path"]["is_nullable"] == "YES"


async def assert_e2f4_public_guest_share_controls(engine: AsyncEngine) -> None:
    """Verify public guest share-control columns and indexes."""

    await assert_c7d9_share_artifact_public_path(engine)
    columns = await column_map(engine, "classroom_planner_share_artifacts")
    assert {
        "guest_snapshot_fingerprint",
        "client_operation_id",
        "revoke_secret_hash",
    }.issubset(columns)
    assert columns["guest_snapshot_fingerprint"]["is_nullable"] == "YES"
    assert columns["client_operation_id"]["is_nullable"] == "YES"
    assert columns["revoke_secret_hash"]["is_nullable"] == "YES"
    indexes = await index_names(engine, "classroom_planner_share_artifacts")
    assert {
        "ix_cp_share_artifacts_public_client_op",
        "ix_cp_share_artifacts_guest_fingerprint",
    }.issubset(indexes)


async def assert_f8a2_share_preview_assets(engine: AsyncEngine) -> None:
    """Verify share preview asset storage."""

    await assert_e2f4_public_guest_share_controls(engine)
    tables = await table_names(engine)
    assert "classroom_planner_share_preview_assets" in tables
    columns = await column_map(engine, "classroom_planner_share_preview_assets")
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
    foreign_keys = await foreign_key_targets(engine, "classroom_planner_share_preview_assets")
    assert foreign_keys["share_id"] == "classroom_planner_share_artifacts"
    delete_rules = await foreign_key_delete_rules(
        engine,
        "classroom_planner_share_preview_assets",
    )
    assert delete_rules["share_id"] == "CASCADE"
    indexes = await index_names(engine, "classroom_planner_share_preview_assets")
    assert {
        "ix_cp_share_preview_assets_source_hash",
        "ix_cp_share_preview_assets_preview_hash",
    }.issubset(indexes)


async def assert_0d9c_fixed_seat_rules(engine: AsyncEngine) -> None:
    """Verify roster-owned fixed-seat smart-rule storage."""

    await assert_f8a2_share_preview_assets(engine)
    tables = await table_names(engine)
    assert "classroom_planner_roster_fixed_seat_rules" in tables
    columns = await column_map(engine, "classroom_planner_roster_fixed_seat_rules")
    assert {"roster_id", "rule_id", "template_id", "student_id", "seat_id"}.issubset(columns)
    foreign_keys = await foreign_key_targets(
        engine,
        "classroom_planner_roster_fixed_seat_rules",
    )
    assert foreign_keys["roster_id"] == "classroom_planner_roster_smart_rule_sets"
    assert foreign_keys["template_id"] == "classroom_planner_room_templates"
    indexes = await index_names(engine, "classroom_planner_roster_fixed_seat_rules")
    assert {
        "ix_classroom_planner_roster_fixed_seat_rules_roster_id",
        "ix_classroom_planner_roster_fixed_seat_rules_template_id",
    }.issubset(indexes)


async def assert_3f6d_use_history_default_on(engine: AsyncEngine) -> None:
    """Verify authenticated draft history defaults to on for new rows."""

    await assert_0d9c_fixed_seat_rules(engine)
    defaults = await column_defaults(engine, "classroom_planner_plan_drafts")
    assert defaults["use_history"] in {"true", "true::boolean"}


async def assert_8a6d_grouping_seating_distance_default_on(engine: AsyncEngine) -> None:
    """Verify authenticated Smart settings default to on for new rows."""

    await assert_3f6d_use_history_default_on(engine)
    defaults = await column_defaults(engine, "classroom_planner_plan_drafts")
    assert defaults["smart_enabled"] in {"true", "true::boolean"}
    assert defaults["grouping_seating_distance_enabled"] in {"true", "true::boolean"}
