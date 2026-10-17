"""One active file per exam, saved exports per format, and server-stored undo history.

The exam workspace used to store one immutable `user_vault_files` row per saved
revision and soft-deleted superseded rows. This revision replaces that format:
one active row per exam lineage, one row per saved export format across active
and trash states, and an `exam_workspace_history` row holding the baseline and
bounded autosave history.

Existing per-version exam rows are test data and are dropped together with
their stored payloads under `<VAULT_ROOT>/<user_id>/<file_id>`, and their bytes
are released from `user_vault_usage`. The vault root comes from the application
`Settings`, so the revision deletes from the same volume the app writes to; a
payload that is already missing is not an error.

Revision ID: 4e9b7d1c6a02
Revises: b7e4d2a9c610
Create Date: 2026-10-17 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import Connection
from sqlalchemy.engine.reflection import Inspector

from skriptoteket.config import Settings

revision: str = "4e9b7d1c6a02"
down_revision: str | Sequence[str] | None = "b7e4d2a9c610"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_VAULT_FILES_TABLE = "user_vault_files"
_USAGE_TABLE = "user_vault_usage"
_HISTORY_TABLE = "exam_workspace_history"

_OLD_VERSION_INDEX = "uq_user_vault_files_document_version"
_EXAM_INDEX = "uq_user_vault_files_document_exam"
_EXPORT_INDEX = "uq_user_vault_files_document_export"

_ARTIFACT_PREFIX = "documents.conversion_hub:exam-workspace"

_EXAM_ROW_PREDICATE = (
    "document_lineage_id IS NOT NULL OR starts_with(source_artifact_id, :artifact_prefix)"
)
_EXAM_INDEX_PREDICATE = (
    "deleted_at IS NULL AND export_format IS NULL AND document_lineage_id IS NOT NULL"
)
_EXPORT_INDEX_PREDICATE = "export_format IS NOT NULL AND document_lineage_id IS NOT NULL"


def _index_names(*, inspector: Inspector, table_name: str) -> set[str]:
    names: set[str] = set()
    for index in inspector.get_indexes(table_name):
        name = index["name"]
        if name is not None:
            names.add(name)
    return names


def _sweep_dropped_payload_files(*, connection: Connection) -> None:
    """Delete the stored payload of every exam row this revision drops.

    The vault stores each payload at ``<VAULT_ROOT>/<user_id>/<file_id>``
    (``LocalVaultStorage._file_path``). The root is read from the application
    ``Settings`` so the sweep targets the mounted vault volume. A payload that
    is already missing is not an error: the row is still dropped and its bytes
    are still released.
    """
    rows = connection.execute(
        sa.text(
            f"""
            SELECT id::text AS file_id, user_id::text AS user_id, bytes
            FROM {_VAULT_FILES_TABLE}
            WHERE {_EXAM_ROW_PREDICATE}
            ORDER BY user_id, id
            """
        ),
        {"artifact_prefix": _ARTIFACT_PREFIX},
    ).all()

    vault_root = Settings().VAULT_ROOT
    deleted_payloads = 0
    missing_payloads = 0
    for row in rows:
        payload_path = vault_root / row.user_id / row.file_id
        try:
            payload_path.unlink()
        except FileNotFoundError:
            missing_payloads += 1
            payload_state = "missing"
        else:
            deleted_payloads += 1
            payload_state = "deleted"
        print(
            "exam_workspace_vault_file_dropped"
            f" user_id={row.user_id} file_id={row.file_id} bytes={row.bytes}"
            f" payload={payload_state}"
        )
    print(
        "exam_workspace_vault_file_storage_swept"
        f" vault_root={vault_root}"
        f" dropped_rows={len(rows)}"
        f" deleted_payloads={deleted_payloads}"
        f" missing_payloads={missing_payloads}"
    )


def _release_dropped_bytes(*, connection: Connection) -> None:
    connection.execute(
        sa.text(
            f"""
            UPDATE {_USAGE_TABLE} AS usage
            SET bytes_total = GREATEST(0, usage.bytes_total - dropped.total_bytes),
                updated_at = now()
            FROM (
                SELECT user_id, SUM(bytes) AS total_bytes
                FROM {_VAULT_FILES_TABLE}
                WHERE deleted_at IS NULL AND ({_EXAM_ROW_PREDICATE})
                GROUP BY user_id
            ) AS dropped
            WHERE usage.user_id = dropped.user_id
            """
        ),
        {"artifact_prefix": _ARTIFACT_PREFIX},
    )


def _delete_dropped_rows(*, connection: Connection) -> None:
    connection.execute(
        sa.text(
            f"""
            DELETE FROM {_VAULT_FILES_TABLE}
            WHERE {_EXAM_ROW_PREDICATE}
            """
        ),
        {"artifact_prefix": _ARTIFACT_PREFIX},
    )


def upgrade() -> None:
    """Replace per-version exam rows with one active exam file and undo history."""

    connection = op.get_bind()
    inspector = inspect(connection)

    if _OLD_VERSION_INDEX in _index_names(inspector=inspector, table_name=_VAULT_FILES_TABLE):
        op.drop_index(_OLD_VERSION_INDEX, table_name=_VAULT_FILES_TABLE)

    columns = {column["name"] for column in inspector.get_columns(_VAULT_FILES_TABLE)}
    if "export_format" not in columns:
        op.add_column(
            _VAULT_FILES_TABLE,
            sa.Column("export_format", sa.String(length=16), nullable=True),
        )
    if "document_saved_at" not in columns:
        op.add_column(
            _VAULT_FILES_TABLE,
            sa.Column("document_saved_at", sa.DateTime(timezone=True), nullable=True),
        )
    if "trashed_with_exam" not in columns:
        op.add_column(
            _VAULT_FILES_TABLE,
            sa.Column(
                "trashed_with_exam",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
        )

    _sweep_dropped_payload_files(connection=connection)
    _release_dropped_bytes(connection=connection)
    _delete_dropped_rows(connection=connection)

    refreshed = inspect(connection)
    index_names = _index_names(inspector=refreshed, table_name=_VAULT_FILES_TABLE)
    if _EXAM_INDEX not in index_names:
        op.create_index(
            _EXAM_INDEX,
            _VAULT_FILES_TABLE,
            ["user_id", "document_lineage_id"],
            unique=True,
            postgresql_where=sa.text(_EXAM_INDEX_PREDICATE),
        )
    if _EXPORT_INDEX not in index_names:
        op.create_index(
            _EXPORT_INDEX,
            _VAULT_FILES_TABLE,
            ["user_id", "document_lineage_id", "export_format"],
            unique=True,
            postgresql_where=sa.text(_EXPORT_INDEX_PREDICATE),
        )

    if _HISTORY_TABLE not in set(refreshed.get_table_names()):
        op.create_table(
            _HISTORY_TABLE,
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("lineage_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("content", sa.LargeBinary(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("user_id", "lineage_id"),
        )


def downgrade() -> None:
    """Restore the per-version index; dropped exam rows and undo history stay gone."""

    connection = op.get_bind()
    inspector = inspect(connection)

    if _HISTORY_TABLE in set(inspector.get_table_names()):
        op.drop_table(_HISTORY_TABLE)

    index_names = _index_names(inspector=inspector, table_name=_VAULT_FILES_TABLE)
    if _EXPORT_INDEX in index_names:
        op.drop_index(_EXPORT_INDEX, table_name=_VAULT_FILES_TABLE)
    if _EXAM_INDEX in index_names:
        op.drop_index(_EXAM_INDEX, table_name=_VAULT_FILES_TABLE)

    columns = {column["name"] for column in inspector.get_columns(_VAULT_FILES_TABLE)}
    if "trashed_with_exam" in columns:
        op.drop_column(_VAULT_FILES_TABLE, "trashed_with_exam")
    if "document_saved_at" in columns:
        op.drop_column(_VAULT_FILES_TABLE, "document_saved_at")
    if "export_format" in columns:
        op.drop_column(_VAULT_FILES_TABLE, "export_format")

    refreshed = inspect(connection)
    if _OLD_VERSION_INDEX not in _index_names(inspector=refreshed, table_name=_VAULT_FILES_TABLE):
        op.create_index(
            _OLD_VERSION_INDEX,
            _VAULT_FILES_TABLE,
            ["user_id", "document_lineage_id", "document_version"],
            unique=True,
            postgresql_where=sa.text("document_lineage_id IS NOT NULL"),
        )
