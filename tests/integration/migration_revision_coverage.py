"""Covered revision IDs for migration idempotency tests.

Purpose:
    Keep the explicit Alembic revision coverage list separate from individual
    schema assertion functions.

Relationships:
    - Imported by `migration_schema_assertions`.
    - Consumed by the parametrized migration idempotency test.
"""

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
    "0d9c5e8a2f31",
    "3f6d8a2c4b91",
    "8a6d4c2f1b09",
    "f2a7c9d4e6b8",
    "b6c9f2a1d4e8",
    "9b2f4c6d8e10",
    "b3e7a1c9d4f2",
    "c4e8f0a2d6b9",
    "d7c9a1e4b6f2",
    "e1f2a3b4c5d6",
    "e9a4b6c8d2f0",
    "f4c8e2a6b9d1",
)
