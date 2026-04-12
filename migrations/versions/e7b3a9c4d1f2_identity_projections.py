"""Add realm-aware identity projections.

Purpose:
    Move HuleEdu subject mappings from `users.external_id` into a dedicated
    product realm projection table and add an audit surface for provisioning.

Relationships:
    - Backfills PR-0255 `auth_provider=huleedu` rows as `huleedu_school`
      projections before dropping the legacy user column.
    - Supports `PR-0258` app-continuation and first-login provisioning.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone
from uuid import uuid4

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text
from sqlalchemy.dialects import postgresql

revision: str = "e7b3a9c4d1f2"
down_revision: str | Sequence[str] | None = "c1d2e3f4a5b6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_USERS_TABLE = "users"
_PROJECTIONS_TABLE = "identity_projections"
_EVENTS_TABLE = "identity_projection_events"
_LEGACY_EXTERNAL_INDEX = "ix_users_external_id"
_LEGACY_EXTERNAL_UNIQUE = "uq_users_auth_provider_external_id"
_PROJECTION_UNIQUE = "uq_identity_projections_realm_subject"
_HULEEDU_SCHOOL_REALM = "huleedu_school"


def _table_exists(table_name: str) -> bool:
    inspector = inspect(op.get_bind())
    return table_name in set(inspector.get_table_names())


def _column_exists(*, table_name: str, column_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    inspector = inspect(op.get_bind())
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _index_exists(*, table_name: str, index_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    inspector = inspect(op.get_bind())
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def _unique_constraint_exists(*, table_name: str, constraint_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    inspector = inspect(op.get_bind())
    return any(
        constraint["name"] == constraint_name
        for constraint in inspector.get_unique_constraints(table_name)
    )


def _create_projection_table() -> None:
    if _table_exists(_PROJECTIONS_TABLE):
        return

    op.create_table(
        _PROJECTIONS_TABLE,
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_identity_realm", sa.String(length=64), nullable=False),
        sa.Column("realm_subject_id", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "product_identity_realm",
            "realm_subject_id",
            name=_PROJECTION_UNIQUE,
        ),
    )
    op.create_index("ix_identity_projections_user_id", _PROJECTIONS_TABLE, ["user_id"])


def _create_event_table() -> None:
    if _table_exists(_EVENTS_TABLE):
        return

    op.create_table(
        _EVENTS_TABLE,
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("projection_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("product_identity_realm", sa.String(length=64), nullable=True),
        sa.Column("realm_subject_id", sa.String(length=255), nullable=True),
        sa.Column("reason_code", sa.String(length=128), nullable=False),
        sa.Column("correlation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("context_jti", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["projection_id"], ["identity_projections.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_identity_projection_events_user_id", _EVENTS_TABLE, ["user_id"])
    op.create_index(
        "ix_identity_projection_events_projection_id",
        _EVENTS_TABLE,
        ["projection_id"],
    )
    op.create_index("ix_identity_projection_events_created_at", _EVENTS_TABLE, ["created_at"])
    op.create_index("ix_identity_projection_events_type", _EVENTS_TABLE, ["event_type"])


def _record_migration_blocked(*, reason_code: str) -> None:
    if not _table_exists(_EVENTS_TABLE):
        return

    op.bulk_insert(
        _event_table(),
        [
            {
                "id": uuid4(),
                "event_type": "migration_blocked",
                "user_id": None,
                "projection_id": None,
                "product_identity_realm": _HULEEDU_SCHOOL_REALM,
                "realm_subject_id": None,
                "reason_code": reason_code,
                "correlation_id": None,
                "context_jti": None,
                "created_at": datetime.now(timezone.utc),
            }
        ],
    )


def _event_table() -> sa.TableClause:
    return sa.table(
        _EVENTS_TABLE,
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("event_type", sa.String()),
        sa.column("user_id", postgresql.UUID(as_uuid=True)),
        sa.column("projection_id", postgresql.UUID(as_uuid=True)),
        sa.column("product_identity_realm", sa.String()),
        sa.column("realm_subject_id", sa.String()),
        sa.column("reason_code", sa.String()),
        sa.column("correlation_id", postgresql.UUID(as_uuid=True)),
        sa.column("context_jti", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )


def _projection_table() -> sa.TableClause:
    return sa.table(
        _PROJECTIONS_TABLE,
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("user_id", postgresql.UUID(as_uuid=True)),
        sa.column("product_identity_realm", sa.String()),
        sa.column("realm_subject_id", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )


def _preflight_legacy_user_subjects() -> None:
    bind = op.get_bind()

    blank_huleedu_count = bind.execute(
        text(
            """
            SELECT COUNT(*)
            FROM users
            WHERE auth_provider = 'huleedu'
              AND (external_id IS NULL OR btrim(external_id) = '')
            """
        )
    ).scalar_one()
    if int(blank_huleedu_count) > 0:
        _record_migration_blocked(reason_code="blank_huleedu_external_id")
        raise RuntimeError("Cannot migrate HuleEdu users with blank external_id values")

    duplicate_rows = bind.execute(
        text(
            """
            SELECT external_id
            FROM users
            WHERE auth_provider = 'huleedu'
              AND external_id IS NOT NULL
              AND btrim(external_id) <> ''
            GROUP BY external_id
            HAVING COUNT(*) > 1
            """
        )
    ).fetchall()
    if duplicate_rows:
        _record_migration_blocked(reason_code="duplicate_huleedu_external_id")
        raise RuntimeError("Cannot migrate duplicate HuleEdu external_id values")

    unexpected_count = bind.execute(
        text(
            """
            SELECT COUNT(*)
            FROM users
            WHERE auth_provider <> 'huleedu'
              AND external_id IS NOT NULL
              AND btrim(external_id) <> ''
            """
        )
    ).scalar_one()
    if int(unexpected_count) > 0:
        _record_migration_blocked(reason_code="unexpected_provider_external_id")
        raise RuntimeError("Cannot migrate non-HuleEdu users with external_id values")


def _backfill_huleedu_school_projections() -> None:
    bind = op.get_bind()
    rows = bind.execute(
        text(
            """
            SELECT id, external_id, created_at, updated_at
            FROM users
            WHERE auth_provider = 'huleedu'
              AND external_id IS NOT NULL
              AND btrim(external_id) <> ''
            """
        )
    ).mappings()
    projections: list[dict[str, object]] = []
    events: list[dict[str, object]] = []
    now = datetime.now(timezone.utc)

    for row in rows:
        projection_id = uuid4()
        projections.append(
            {
                "id": projection_id,
                "user_id": row["id"],
                "product_identity_realm": _HULEEDU_SCHOOL_REALM,
                "realm_subject_id": row["external_id"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
        )
        events.append(
            {
                "id": uuid4(),
                "event_type": "migration_backfilled",
                "user_id": row["id"],
                "projection_id": projection_id,
                "product_identity_realm": _HULEEDU_SCHOOL_REALM,
                "realm_subject_id": row["external_id"],
                "reason_code": "legacy_huleedu_external_id",
                "correlation_id": None,
                "context_jti": None,
                "created_at": now,
            }
        )

    if projections:
        op.bulk_insert(_projection_table(), projections)
        op.bulk_insert(_event_table(), events)


def upgrade() -> None:
    """Create projection/audit tables, backfill legacy subjects, and drop `external_id`."""
    _create_projection_table()
    _create_event_table()

    if _column_exists(table_name=_USERS_TABLE, column_name="external_id"):
        _preflight_legacy_user_subjects()
        _backfill_huleedu_school_projections()

        if _unique_constraint_exists(
            table_name=_USERS_TABLE,
            constraint_name=_LEGACY_EXTERNAL_UNIQUE,
        ):
            op.drop_constraint(_LEGACY_EXTERNAL_UNIQUE, _USERS_TABLE, type_="unique")
        if _index_exists(table_name=_USERS_TABLE, index_name=_LEGACY_EXTERNAL_INDEX):
            op.drop_index(_LEGACY_EXTERNAL_INDEX, table_name=_USERS_TABLE)
        op.drop_column(_USERS_TABLE, "external_id")


def downgrade() -> None:
    """Restore the legacy user column from huleedu_school projections for recovery."""
    if not _column_exists(table_name=_USERS_TABLE, column_name="external_id"):
        op.add_column(_USERS_TABLE, sa.Column("external_id", sa.String(length=255), nullable=True))

    if _table_exists(_PROJECTIONS_TABLE):
        op.get_bind().execute(
            text(
                """
                UPDATE users
                   SET external_id = identity_projections.realm_subject_id
                  FROM identity_projections
                 WHERE users.id = identity_projections.user_id
                   AND users.auth_provider = 'huleedu'
                   AND identity_projections.product_identity_realm = :realm
                """
            ),
            {"realm": _HULEEDU_SCHOOL_REALM},
        )

    if not _unique_constraint_exists(
        table_name=_USERS_TABLE,
        constraint_name=_LEGACY_EXTERNAL_UNIQUE,
    ):
        op.create_unique_constraint(
            _LEGACY_EXTERNAL_UNIQUE,
            _USERS_TABLE,
            ["auth_provider", "external_id"],
        )
    if not _index_exists(table_name=_USERS_TABLE, index_name=_LEGACY_EXTERNAL_INDEX):
        op.create_index(_LEGACY_EXTERNAL_INDEX, _USERS_TABLE, ["external_id"])

    if _table_exists(_EVENTS_TABLE):
        op.drop_table(_EVENTS_TABLE)
    if _table_exists(_PROJECTIONS_TABLE):
        op.drop_table(_PROJECTIONS_TABLE)
