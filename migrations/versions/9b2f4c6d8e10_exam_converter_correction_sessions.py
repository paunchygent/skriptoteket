"""Add Exam Converter correction sessions.

Revision ID: 9b2f4c6d8e10
Revises: b6c9f2a1d4e8
Create Date: 2026-05-19 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "9b2f4c6d8e10"
down_revision: str | Sequence[str] | None = "b6c9f2a1d4e8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create durable correction-session tables for authenticated Exam Converter."""

    op.create_table(
        "exam_converter_correction_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversion_hub_job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_authoring_schema_version", sa.String(length=64), nullable=False),
        sa.Column("source_bundle_id", sa.String(length=255), nullable=True),
        sa.Column("source_file_sha256", sa.String(length=128), nullable=True),
        sa.Column("source_state_sha256", sa.String(length=128), nullable=False),
        sa.Column("source_state_signature", sa.Text(), nullable=False),
        sa.Column("session_version", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("session_version >= 0", name="ck_exam_conv_corr_session_version"),
        sa.ForeignKeyConstraint(
            ["conversion_hub_job_id"], ["conversion_hub_jobs.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_exam_converter_correction_sessions_owner_user_id",
        "exam_converter_correction_sessions",
        ["owner_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_exam_converter_correction_sessions_job_id",
        "exam_converter_correction_sessions",
        ["conversion_hub_job_id"],
        unique=False,
    )
    op.create_index(
        "ix_exam_conv_corr_sessions_owner_updated",
        "exam_converter_correction_sessions",
        ["owner_user_id", "updated_at"],
        unique=False,
    )
    op.create_index(
        "uq_exam_conv_corr_sessions_owner_job",
        "exam_converter_correction_sessions",
        ["owner_user_id", "conversion_hub_job_id"],
        unique=True,
    )

    op.create_table(
        "exam_converter_correction_intents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entry_id", sa.String(length=255), nullable=False),
        sa.Column("correction_kind", sa.String(length=64), nullable=False),
        sa.Column("target_key", sa.Text(), nullable=False),
        sa.Column("conflict_family", sa.Text(), nullable=True),
        sa.Column("item_id", sa.String(length=128), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("item_type", sa.String(length=64), nullable=False),
        sa.Column("source_item_fingerprint", sa.String(length=128), nullable=False),
        sa.Column("source_binding", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("target", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("sequence >= 1", name="ck_exam_conv_corr_intent_sequence"),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["exam_converter_correction_sessions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_exam_converter_correction_intents_session_id",
        "exam_converter_correction_intents",
        ["session_id"],
        unique=False,
    )
    op.create_index(
        "ix_exam_conv_corr_intents_session_active",
        "exam_converter_correction_intents",
        ["session_id", "is_active"],
        unique=False,
    )
    op.create_index(
        "uq_exam_conv_corr_intents_active_target",
        "exam_converter_correction_intents",
        ["session_id", "target_key"],
        unique=True,
        postgresql_where=sa.text("is_active IS TRUE"),
    )
    op.create_index(
        "uq_exam_conv_corr_intents_active_family",
        "exam_converter_correction_intents",
        ["session_id", "conflict_family"],
        unique=True,
        postgresql_where=sa.text("is_active IS TRUE AND conflict_family IS NOT NULL"),
    )


def downgrade() -> None:
    """Drop durable correction-session tables."""

    op.drop_index(
        "uq_exam_conv_corr_intents_active_family",
        table_name="exam_converter_correction_intents",
    )
    op.drop_index(
        "uq_exam_conv_corr_intents_active_target",
        table_name="exam_converter_correction_intents",
    )
    op.drop_index(
        "ix_exam_conv_corr_intents_session_active",
        table_name="exam_converter_correction_intents",
    )
    op.drop_index(
        "ix_exam_converter_correction_intents_session_id",
        table_name="exam_converter_correction_intents",
    )
    op.drop_table("exam_converter_correction_intents")
    op.drop_index(
        "uq_exam_conv_corr_sessions_owner_job",
        table_name="exam_converter_correction_sessions",
    )
    op.drop_index(
        "ix_exam_conv_corr_sessions_owner_updated",
        table_name="exam_converter_correction_sessions",
    )
    op.drop_index(
        "ix_exam_converter_correction_sessions_job_id",
        table_name="exam_converter_correction_sessions",
    )
    op.drop_index(
        "ix_exam_converter_correction_sessions_owner_user_id",
        table_name="exam_converter_correction_sessions",
    )
    op.drop_table("exam_converter_correction_sessions")
