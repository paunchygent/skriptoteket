"""Identity, profile, and account migration schema assertions.

Purpose:
    Verify identity, profile, account-session, favorite-app, and file-vault
    schema revisions during idempotent Alembic tests.

Relationships:
    - Registered by `migration_schema_assertions`.
    - Uses shared information-schema helpers from `migration_schema_helpers`.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine

from tests.integration.migration_schema_helpers import (
    column_map,
    index_names,
    table_names,
)


async def assert_0001_init(engine: AsyncEngine) -> None:
    tables = await table_names(engine)
    assert {"users", "sessions"}.issubset(tables)
    assert "ix_users_email" in await index_names(engine, "users")
    assert "ix_users_external_id" in await index_names(engine, "users")
    assert "ix_sessions_user_id" in await index_names(engine, "sessions")
    assert "ix_sessions_expires_at" in await index_names(engine, "sessions")


async def assert_0012_tool_owner_user_id(engine: AsyncEngine) -> None:
    columns = await column_map(engine, "tools")
    assert "owner_user_id" in columns
    assert columns["owner_user_id"]["is_nullable"] == "NO"
    assert "ix_tools_owner_user_id" in await index_names(engine, "tools")


async def assert_0014_tool_versions_settings(engine: AsyncEngine) -> None:
    assert "settings_schema" in await column_map(engine, "tool_versions")


async def assert_0022_email_verification_tokens(engine: AsyncEngine) -> None:
    tables = await table_names(engine)
    assert "email_verification_tokens" in tables
    indexes = await index_names(engine, "email_verification_tokens")
    assert {
        "ix_email_verification_tokens_user_id",
        "ix_email_verification_tokens_token",
        "ix_email_verification_tokens_expires_at",
    }.issubset(indexes)


async def assert_0026_profile_ai_settings(engine: AsyncEngine) -> None:
    assert "allow_remote_fallback" in await column_map(engine, "user_profiles")


async def assert_1eb5_profile_tutorial_seen_sections(engine: AsyncEngine) -> None:
    columns = await column_map(engine, "user_profiles")
    assert columns["classroom_planner_tutorial_seen_sections"]["is_nullable"] == "YES"


async def assert_8f3d_password_reset_tokens(engine: AsyncEngine) -> None:
    tables = await table_names(engine)
    assert "password_reset_tokens" in tables
    indexes = await index_names(engine, "password_reset_tokens")
    assert {
        "ix_password_reset_tokens_user_id",
        "ix_password_reset_tokens_token_hash",
        "ix_password_reset_tokens_expires_at",
    }.issubset(indexes)
    columns = await column_map(engine, "password_reset_tokens")
    assert {"user_id", "token_hash", "expires_at", "used_at", "created_at"}.issubset(columns)


async def assert_a1e4_default_klassrumskartan_favorite(engine: AsyncEngine) -> None:
    await assert_8f3d_password_reset_tokens(engine)
    tables = await table_names(engine)
    assert "user_favorite_apps" in tables


async def assert_b7f9_drop_legacy_student_notes(engine: AsyncEngine) -> None:
    await assert_a1e4_default_klassrumskartan_favorite(engine)
    tables = await table_names(engine)
    assert "classroom_planner_student_planning_meta" not in tables


async def assert_d3a9_guest_upgrade_identity(engine: AsyncEngine) -> None:
    await assert_b7f9_drop_legacy_student_notes(engine)
    columns = await column_map(engine, "classroom_planner_plan_drafts")
    assert {
        "task_entry_classroom_selection_mode",
        "guest_import_identity",
    }.issubset(columns)
    indexes = await index_names(engine, "classroom_planner_plan_drafts")
    assert "uq_cp_guest_import_identity" in indexes


async def assert_c1d2_drop_browser_auth_sessions(engine: AsyncEngine) -> None:
    await assert_d3a9_guest_upgrade_identity(engine)
    tables = await table_names(engine)
    assert "sessions" not in tables
    assert "tool_sessions" in tables


async def assert_0032_user_file_vault(engine: AsyncEngine) -> None:
    tables = await table_names(engine)
    assert {"user_vault_files", "user_vault_usage"}.issubset(tables)
    indexes = await index_names(engine, "user_vault_files")
    assert {
        "ix_user_vault_files_user_id",
        "ix_user_vault_files_deleted_at",
        "ix_user_vault_files_source_run_id",
    }.issubset(indexes)
