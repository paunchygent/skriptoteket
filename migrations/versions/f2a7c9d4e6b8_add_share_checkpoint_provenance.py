"""Add share-artifact provenance to classroom-planner checkpoints.

Purpose:
    Allow authenticated Klassrumskartan share links to create the same
    Smart-history checkpoints as PDF/Excel exports while retaining explicit
    source provenance for existing export-job rows.

Relationships:
    - Extends seating and grouping checkpoint tables created by the Smart
      history slices.
    - References immutable classroom planner share artifacts without changing
      public share read semantics.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f2a7c9d4e6b8"
down_revision: str | Sequence[str] | None = "8a6d4c2f1b09"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SEATING_TABLE = "classroom_planner_seating_export_checkpoints"
_GROUPING_TABLE = "classroom_planner_grouping_export_checkpoints"
_SHARES_TABLE = "classroom_planner_share_artifacts"


def upgrade() -> None:
    """Add provenance columns and source constraints for checkpoint rows."""

    _add_share_provenance(
        table_name=_SEATING_TABLE,
        share_index_name="uq_cp_seating_export_checkpoints_source_share",
        share_fk_name="fk_cp_seating_export_checkpoints_source_share",
        kind_check_name="ck_cp_seating_export_checkpoints_source_kind",
        source_check_name="ck_cp_seating_export_checkpoints_one_source",
    )
    _add_share_provenance(
        table_name=_GROUPING_TABLE,
        share_index_name="uq_cp_grouping_export_checkpoints_source_share",
        share_fk_name="fk_cp_grouping_export_checkpoints_source_share",
        kind_check_name="ck_cp_grouping_export_checkpoints_source_kind",
        source_check_name="ck_cp_grouping_export_checkpoints_one_source",
    )


def downgrade() -> None:
    """Restore export-job-only checkpoint provenance."""

    _drop_share_provenance(
        table_name=_GROUPING_TABLE,
        share_index_name="uq_cp_grouping_export_checkpoints_source_share",
        share_fk_name="fk_cp_grouping_export_checkpoints_source_share",
        kind_check_name="ck_cp_grouping_export_checkpoints_source_kind",
        source_check_name="ck_cp_grouping_export_checkpoints_one_source",
    )
    _drop_share_provenance(
        table_name=_SEATING_TABLE,
        share_index_name="uq_cp_seating_export_checkpoints_source_share",
        share_fk_name="fk_cp_seating_export_checkpoints_source_share",
        kind_check_name="ck_cp_seating_export_checkpoints_source_kind",
        source_check_name="ck_cp_seating_export_checkpoints_one_source",
    )


def _add_share_provenance(
    *,
    table_name: str,
    share_index_name: str,
    share_fk_name: str,
    kind_check_name: str,
    source_check_name: str,
) -> None:
    op.add_column(
        table_name,
        sa.Column(
            "source_kind",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'export_job'"),
        ),
    )
    op.add_column(
        table_name,
        sa.Column(
            "source_share_artifact_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.alter_column(
        table_name,
        "source_export_job_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    op.create_foreign_key(
        share_fk_name,
        table_name,
        _SHARES_TABLE,
        ["source_share_artifact_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        share_index_name,
        table_name,
        ["source_share_artifact_id"],
        unique=True,
    )
    op.create_check_constraint(
        kind_check_name,
        table_name,
        "source_kind IN ('export_job', 'share_artifact')",
    )
    op.create_check_constraint(
        source_check_name,
        table_name,
        "("
        "source_kind = 'export_job' "
        "AND source_export_job_id IS NOT NULL "
        "AND source_share_artifact_id IS NULL"
        ") OR ("
        "source_kind = 'share_artifact' "
        "AND source_export_job_id IS NULL "
        "AND source_share_artifact_id IS NOT NULL"
        ")",
    )


def _drop_share_provenance(
    *,
    table_name: str,
    share_index_name: str,
    share_fk_name: str,
    kind_check_name: str,
    source_check_name: str,
) -> None:
    op.execute(sa.text(f"DELETE FROM {table_name} WHERE source_kind = 'share_artifact'"))
    op.drop_constraint(source_check_name, table_name, type_="check")
    op.drop_constraint(kind_check_name, table_name, type_="check")
    op.drop_index(share_index_name, table_name=table_name)
    op.drop_constraint(share_fk_name, table_name, type_="foreignkey")
    op.alter_column(
        table_name,
        "source_export_job_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.drop_column(table_name, "source_share_artifact_id")
    op.drop_column(table_name, "source_kind")
