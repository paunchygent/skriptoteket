"""Make input_schema non-null and migrate legacy null semantics.

Revision ID: 0023
Revises: 0022
Create Date: 2026-01-02
"""

from __future__ import annotations

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "0023_input_schema_not_null"
down_revision: str | None = "0022_email_verification_tokens"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_DEFAULT_INPUT_SCHEMA_SERVER_DEFAULT = sa.text("'[]'::jsonb")
_LEGACY_FILE_INPUT_SCHEMA = [
    {
        "kind": "file",
        "name": "files",
        "label": "Filer",
        "min": 1,
        "max": 10,
    }
]


def _table_has_column(*, inspector, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _migrate_null_input_schema_to_file_field(*, table_name: str) -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    if table_name not in set(inspector.get_table_names()):
        return
    if not _table_has_column(
        inspector=inspector, table_name=table_name, column_name="input_schema"
    ):
        return

    payload = json.dumps(_LEGACY_FILE_INPUT_SCHEMA, ensure_ascii=False, separators=(",", ":"))
    op.execute(
        sa.text(
            f"UPDATE {table_name} SET input_schema = (:payload)::jsonb "
            "WHERE input_schema IS NULL OR input_schema = 'null'::jsonb"
        ).bindparams(payload=payload)
    )


def _ensure_input_schema_not_null(*, table_name: str) -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    if table_name not in set(inspector.get_table_names()):
        return
    if not _table_has_column(
        inspector=inspector, table_name=table_name, column_name="input_schema"
    ):
        return

    columns = {column["name"]: column for column in inspector.get_columns(table_name)}
    input_schema_column = columns.get("input_schema")
    if input_schema_column is None:
        return

    if input_schema_column.get("nullable", True):
        op.alter_column(
            table_name,
            "input_schema",
            existing_type=postgresql.JSONB(),
            nullable=False,
            server_default=_DEFAULT_INPUT_SCHEMA_SERVER_DEFAULT,
        )
    else:
        # Even if NOT NULL is already set, ensure the server default is correct.
        op.alter_column(
            table_name,
            "input_schema",
            existing_type=postgresql.JSONB(),
            server_default=_DEFAULT_INPUT_SCHEMA_SERVER_DEFAULT,
        )


def upgrade() -> None:
    _migrate_null_input_schema_to_file_field(table_name="tool_versions")
    _ensure_input_schema_not_null(table_name="tool_versions")

    _migrate_null_input_schema_to_file_field(table_name="sandbox_snapshots")
    _ensure_input_schema_not_null(table_name="sandbox_snapshots")


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = set(inspector.get_table_names())

    if "tool_versions" in tables and _table_has_column(
        inspector=inspector, table_name="tool_versions", column_name="input_schema"
    ):
        op.alter_column(
            "tool_versions",
            "input_schema",
            existing_type=postgresql.JSONB(),
            nullable=True,
            server_default=None,
        )

    if "sandbox_snapshots" in tables and _table_has_column(
        inspector=inspector, table_name="sandbox_snapshots", column_name="input_schema"
    ):
        op.alter_column(
            "sandbox_snapshots",
            "input_schema",
            existing_type=postgresql.JSONB(),
            nullable=True,
            server_default=None,
        )
