"""Add the durable public Exam Converter job queue."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a6d4e8f2c1b9"
down_revision: str | Sequence[str] | None = "c8e4f2a6d9b1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "public_exam_converter_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("requested_targets", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_filename", sa.String(length=255), nullable=False),
        sa.Column("source_content_type", sa.String(length=255), nullable=False),
        sa.Column("source_dxe", sa.LargeBinary(), nullable=False),
        sa.Column("graded_result_filename", sa.String(length=255), nullable=True),
        sa.Column("graded_result_content_type", sa.String(length=255), nullable=True),
        sa.Column("graded_result_pdf", sa.LargeBinary(), nullable=True),
        sa.Column("correlation_id", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("locked_by", sa.String(length=128), nullable=True),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_public_exam_converter_jobs_claim",
        "public_exam_converter_jobs",
        ["status", "submitted_at"],
    )
    op.create_index(
        op.f("ix_public_exam_converter_jobs_expires_at"),
        "public_exam_converter_jobs",
        ["expires_at"],
    )
    op.create_index(
        op.f("ix_public_exam_converter_jobs_status"),
        "public_exam_converter_jobs",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_public_exam_converter_jobs_status"),
        table_name="public_exam_converter_jobs",
    )
    op.drop_index(
        op.f("ix_public_exam_converter_jobs_expires_at"),
        table_name="public_exam_converter_jobs",
    )
    op.drop_index(
        "ix_public_exam_converter_jobs_claim",
        table_name="public_exam_converter_jobs",
    )
    op.drop_table("public_exam_converter_jobs")
