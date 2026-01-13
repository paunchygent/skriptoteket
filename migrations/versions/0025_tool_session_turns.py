"""Add tool_session_turns + turn_id on tool_session_messages.

Revision ID: 0025_tool_session_turns
Revises: 0024_tool_session_messages
Create Date: 2026-01-12
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "0025_tool_session_turns"
down_revision: str | None = "0024_tool_session_messages"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TURN_STATUS_COMPLETE = "complete"
_TURN_STATUS_FAILED = "failed"
_TURN_STATUS_CANCELLED = "cancelled"  # reserved for runtime; migration uses failed/complete only


def _table_has_column(*, inspector, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _has_index(*, inspector, table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def _has_unique_constraint(*, inspector, table_name: str, name: str) -> bool:
    return any(
        constraint["name"] == name for constraint in inspector.get_unique_constraints(table_name)
    )


def _has_foreign_key(*, inspector, table_name: str, name: str) -> bool:
    return any(key["name"] == name for key in inspector.get_foreign_keys(table_name))


def _turn_status_for_assistant_meta(meta: dict[str, object] | None) -> tuple[str, str | None]:
    if not isinstance(meta, dict):
        return _TURN_STATUS_COMPLETE, None
    raw_outcome = meta.get("stream_outcome")
    if isinstance(raw_outcome, str) and raw_outcome:
        return _TURN_STATUS_FAILED, raw_outcome
    if meta.get("orphaned") is True:
        return _TURN_STATUS_FAILED, "orphaned_assistant"
    return _TURN_STATUS_COMPLETE, None


def _ensure_turns_table_exists(*, inspector) -> None:
    tables = set(inspector.get_table_names())
    if "tool_session_turns" in tables:
        return

    op.create_table(
        "tool_session_turns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tool_session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tool_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("failure_outcome", sa.String(64), nullable=True),
        sa.Column("provider", sa.String(32), nullable=True),
        sa.Column("correlation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sequence", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "tool_session_id",
            "id",
            name="uq_tool_session_turns_session_turn_id",
        ),
    )

    op.create_index(
        "ix_tool_session_turns_session_sequence",
        "tool_session_turns",
        ["tool_session_id", "sequence"],
    )
    op.create_index(
        "uq_tool_session_turns_one_pending_per_session",
        "tool_session_turns",
        ["tool_session_id"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )


def _ensure_turns_indexes(*, inspector) -> None:
    if "tool_session_turns" not in set(inspector.get_table_names()):
        return

    if not _has_index(
        inspector=inspector,
        table_name="tool_session_turns",
        index_name="ix_tool_session_turns_session_sequence",
    ):
        op.create_index(
            "ix_tool_session_turns_session_sequence",
            "tool_session_turns",
            ["tool_session_id", "sequence"],
        )

    if not _has_index(
        inspector=inspector,
        table_name="tool_session_turns",
        index_name="uq_tool_session_turns_one_pending_per_session",
    ):
        op.create_index(
            "uq_tool_session_turns_one_pending_per_session",
            "tool_session_turns",
            ["tool_session_id"],
            unique=True,
            postgresql_where=sa.text("status = 'pending'"),
        )


def _ensure_turn_id_column(*, inspector) -> None:
    tables = set(inspector.get_table_names())
    if "tool_session_messages" not in tables:
        return
    if not _table_has_column(
        inspector=inspector, table_name="tool_session_messages", column_name="turn_id"
    ):
        op.add_column(
            "tool_session_messages",
            sa.Column("turn_id", postgresql.UUID(as_uuid=True), nullable=True),
        )

    # Ensure join-friendly index exists even if the column pre-existed.
    if not _has_index(
        inspector=inspector,
        table_name="tool_session_messages",
        index_name="ix_tool_session_messages_session_turn_id",
    ):
        op.create_index(
            "ix_tool_session_messages_session_turn_id",
            "tool_session_messages",
            ["tool_session_id", "turn_id"],
        )


def _ensure_message_turn_constraints(*, inspector) -> None:
    tables = set(inspector.get_table_names())
    if "tool_session_messages" not in tables:
        return

    if not _has_unique_constraint(
        inspector=inspector,
        table_name="tool_session_messages",
        name="uq_tool_session_messages_turn_role",
    ):
        op.create_unique_constraint(
            "uq_tool_session_messages_turn_role",
            "tool_session_messages",
            ["tool_session_id", "turn_id", "role"],
        )

    if not _has_foreign_key(
        inspector=inspector,
        table_name="tool_session_messages",
        name="fk_tool_session_messages_turn",
    ):
        op.create_foreign_key(
            "fk_tool_session_messages_turn",
            "tool_session_messages",
            "tool_session_turns",
            ["tool_session_id", "turn_id"],
            ["tool_session_id", "id"],
            ondelete="CASCADE",
        )


def _ensure_message_turn_id_not_null(*, inspector) -> None:
    tables = set(inspector.get_table_names())
    if "tool_session_messages" not in tables:
        return
    if not _table_has_column(
        inspector=inspector, table_name="tool_session_messages", column_name="turn_id"
    ):
        return

    columns = {column["name"]: column for column in inspector.get_columns("tool_session_messages")}
    turn_id = columns.get("turn_id")
    if turn_id is None:
        return
    if not turn_id.get("nullable", True):
        return

    op.alter_column(
        "tool_session_messages",
        "turn_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )


def _delete_legacy_virtual_file_context_messages(*, conn) -> None:
    conn.execute(
        sa.text("DELETE FROM tool_session_messages WHERE meta->>'kind' = 'virtual_file_context'")
    )


def _backfill_turns_and_turn_ids(*, conn, inspector) -> None:
    tables = set(inspector.get_table_names())
    if "tool_session_messages" not in tables:
        return
    if "tool_session_turns" not in tables:
        return
    if not _table_has_column(
        inspector=inspector, table_name="tool_session_messages", column_name="turn_id"
    ):
        return

    needs_backfill = conn.execute(
        sa.text("SELECT 1 FROM tool_session_messages WHERE turn_id IS NULL LIMIT 1")
    ).scalar_one_or_none()
    if needs_backfill is None:
        return

    session_ids = [
        row["tool_session_id"]
        for row in conn.execute(
            sa.text("SELECT DISTINCT tool_session_id FROM tool_session_messages")
        ).mappings()
    ]

    insert_turn_stmt = sa.text(
        "INSERT INTO tool_session_turns (id, tool_session_id, status, failure_outcome) "
        "VALUES (:id, :tool_session_id, :status, :failure_outcome) "
        "ON CONFLICT (id) DO NOTHING"
    )
    update_message_turn_stmt = sa.text(
        "UPDATE tool_session_messages SET turn_id = (:turn_id) "
        "WHERE tool_session_id = (:tool_session_id) AND message_id = (:message_id)"
    )
    insert_message_stmt = sa.text(
        "INSERT INTO tool_session_messages "
        "(id, tool_session_id, message_id, role, content, meta, turn_id) "
        "VALUES (:id, :tool_session_id, :message_id, :role, :content, (:meta)::jsonb, :turn_id) "
        "ON CONFLICT (tool_session_id, message_id) DO NOTHING"
    )

    for tool_session_id in session_ids:
        rows = list(
            conn.execute(
                sa.text(
                    "SELECT message_id, role, meta "
                    "FROM tool_session_messages "
                    "WHERE tool_session_id = (:tool_session_id) "
                    "ORDER BY sequence ASC"
                ).bindparams(tool_session_id=tool_session_id)
            ).mappings()
        )
        pending_user: dict[str, object] | None = None

        def finalize_missing_assistant(*, user_row: dict[str, object]) -> None:
            turn_id = uuid4()
            conn.execute(
                insert_turn_stmt,
                {
                    "id": turn_id,
                    "tool_session_id": tool_session_id,
                    "status": _TURN_STATUS_FAILED,
                    "failure_outcome": "missing_assistant_migrated",
                },
            )
            conn.execute(
                update_message_turn_stmt,
                {
                    "tool_session_id": tool_session_id,
                    "message_id": user_row["message_id"],
                    "turn_id": turn_id,
                },
            )
            conn.execute(
                insert_message_stmt,
                {
                    "id": uuid4(),
                    "tool_session_id": tool_session_id,
                    "message_id": uuid4(),
                    "role": "assistant",
                    "content": "",
                    "meta": json.dumps(
                        {"migrated": True, "kind": "assistant_placeholder"},
                        ensure_ascii=False,
                        separators=(",", ":"),
                    ),
                    "turn_id": turn_id,
                },
            )

        for row in rows:
            role = row.get("role")
            if role == "user":
                if pending_user is not None:
                    finalize_missing_assistant(user_row=pending_user)
                pending_user = row
                continue

            if role != "assistant":
                continue

            if pending_user is None:
                turn_id = uuid4()
                conn.execute(
                    insert_turn_stmt,
                    {
                        "id": turn_id,
                        "tool_session_id": tool_session_id,
                        "status": _TURN_STATUS_FAILED,
                        "failure_outcome": "orphaned_assistant_migrated",
                    },
                )
                hidden_user_meta = {
                    "hidden": True,
                    "kind": "migrated_orphan_user_placeholder",
                }
                conn.execute(
                    insert_message_stmt,
                    {
                        "id": uuid4(),
                        "tool_session_id": tool_session_id,
                        "message_id": uuid4(),
                        "role": "user",
                        "content": "",
                        "meta": json.dumps(
                            hidden_user_meta, ensure_ascii=False, separators=(",", ":")
                        ),
                        "turn_id": turn_id,
                    },
                )
                conn.execute(
                    update_message_turn_stmt,
                    {
                        "tool_session_id": tool_session_id,
                        "message_id": row["message_id"],
                        "turn_id": turn_id,
                    },
                )
                continue

            assistant_meta = row.get("meta") if isinstance(row.get("meta"), dict) else None
            status, failure_outcome = _turn_status_for_assistant_meta(assistant_meta)
            turn_id = uuid4()
            conn.execute(
                insert_turn_stmt,
                {
                    "id": turn_id,
                    "tool_session_id": tool_session_id,
                    "status": status,
                    "failure_outcome": failure_outcome,
                },
            )
            conn.execute(
                update_message_turn_stmt,
                {
                    "tool_session_id": tool_session_id,
                    "message_id": pending_user["message_id"],
                    "turn_id": turn_id,
                },
            )
            conn.execute(
                update_message_turn_stmt,
                {
                    "tool_session_id": tool_session_id,
                    "message_id": row["message_id"],
                    "turn_id": turn_id,
                },
            )
            pending_user = None

        if pending_user is not None:
            finalize_missing_assistant(user_row=pending_user)


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)

    _ensure_turns_table_exists(inspector=inspector)
    inspector = inspect(conn)
    _ensure_turns_indexes(inspector=inspector)

    inspector = inspect(conn)
    _ensure_turn_id_column(inspector=inspector)

    inspector = inspect(conn)
    _delete_legacy_virtual_file_context_messages(conn=conn)

    inspector = inspect(conn)
    _backfill_turns_and_turn_ids(conn=conn, inspector=inspector)

    inspector = inspect(conn)
    _ensure_message_turn_id_not_null(inspector=inspector)

    inspector = inspect(conn)
    _ensure_message_turn_constraints(inspector=inspector)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = set(inspector.get_table_names())

    if "tool_session_messages" in tables:
        if _has_foreign_key(
            inspector=inspector,
            table_name="tool_session_messages",
            name="fk_tool_session_messages_turn",
        ):
            op.drop_constraint(
                "fk_tool_session_messages_turn",
                table_name="tool_session_messages",
                type_="foreignkey",
            )

        if _has_unique_constraint(
            inspector=inspector,
            table_name="tool_session_messages",
            name="uq_tool_session_messages_turn_role",
        ):
            op.drop_constraint(
                "uq_tool_session_messages_turn_role",
                table_name="tool_session_messages",
                type_="unique",
            )

        if _has_index(
            inspector=inspector,
            table_name="tool_session_messages",
            index_name="ix_tool_session_messages_session_turn_id",
        ):
            op.drop_index(
                "ix_tool_session_messages_session_turn_id",
                table_name="tool_session_messages",
            )

        if _table_has_column(
            inspector=inspector,
            table_name="tool_session_messages",
            column_name="turn_id",
        ):
            op.drop_column("tool_session_messages", "turn_id")

    inspector = inspect(conn)
    tables = set(inspector.get_table_names())
    if "tool_session_turns" in tables:
        if _has_index(
            inspector=inspector,
            table_name="tool_session_turns",
            index_name="uq_tool_session_turns_one_pending_per_session",
        ):
            op.drop_index(
                "uq_tool_session_turns_one_pending_per_session",
                table_name="tool_session_turns",
            )
        if _has_index(
            inspector=inspector,
            table_name="tool_session_turns",
            index_name="ix_tool_session_turns_session_sequence",
        ):
            op.drop_index(
                "ix_tool_session_turns_session_sequence",
                table_name="tool_session_turns",
            )
        op.drop_table("tool_session_turns")
