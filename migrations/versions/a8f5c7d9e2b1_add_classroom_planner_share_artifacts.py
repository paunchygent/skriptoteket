"""add classroom planner share artifacts

Revision ID: a8f5c7d9e2b1
Revises: e7b3a9c4d1f2
Create Date: 2026-04-30 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a8f5c7d9e2b1"
down_revision: Union[str, Sequence[str], None] = "e7b3a9c4d1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.create_table(
        "classroom_planner_share_artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=96), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("draft_kind", sa.String(length=32), nullable=False),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("draft_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("roster_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_revision", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("preview_description", sa.String(length=500), nullable=True),
        sa.Column("renderer_version", sa.String(length=64), nullable=False),
        sa.Column("presentation_schema_version", sa.String(length=64), nullable=False),
        sa.Column("presentation_hash", sa.String(length=96), nullable=False),
        sa.Column("content_hash", sa.String(length=96), nullable=False),
        sa.Column("presentation_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("rendered_html", sa.Text(), nullable=False),
        sa.Column("rendered_css", sa.Text(), nullable=False),
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
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["draft_id"],
            ["classroom_planner_plan_drafts.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_classroom_planner_share_artifacts_token_hash",
        "classroom_planner_share_artifacts",
        ["token_hash"],
        unique=True,
    )
    op.create_index(
        "ix_classroom_planner_share_artifacts_source",
        "classroom_planner_share_artifacts",
        ["source"],
        unique=False,
    )
    op.create_index(
        "ix_classroom_planner_share_artifacts_owner_user_id",
        "classroom_planner_share_artifacts",
        ["owner_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_classroom_planner_share_artifacts_draft_id",
        "classroom_planner_share_artifacts",
        ["draft_id"],
        unique=False,
    )
    op.create_index(
        "ix_cp_share_artifacts_owner_draft_kind_created",
        "classroom_planner_share_artifacts",
        ["owner_user_id", "draft_id", "draft_kind", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_cp_share_artifacts_expires_at",
        "classroom_planner_share_artifacts",
        ["expires_at"],
        unique=False,
    )
    op.create_index(
        "ix_cp_share_artifacts_revoked_at",
        "classroom_planner_share_artifacts",
        ["revoked_at"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_index(
        "ix_cp_share_artifacts_revoked_at",
        table_name="classroom_planner_share_artifacts",
    )
    op.drop_index(
        "ix_cp_share_artifacts_expires_at",
        table_name="classroom_planner_share_artifacts",
    )
    op.drop_index(
        "ix_cp_share_artifacts_owner_draft_kind_created",
        table_name="classroom_planner_share_artifacts",
    )
    op.drop_index(
        "ix_classroom_planner_share_artifacts_draft_id",
        table_name="classroom_planner_share_artifacts",
    )
    op.drop_index(
        "ix_classroom_planner_share_artifacts_owner_user_id",
        table_name="classroom_planner_share_artifacts",
    )
    op.drop_index(
        "ix_classroom_planner_share_artifacts_source",
        table_name="classroom_planner_share_artifacts",
    )
    op.drop_index(
        "ix_classroom_planner_share_artifacts_token_hash",
        table_name="classroom_planner_share_artifacts",
    )
    op.drop_table("classroom_planner_share_artifacts")
