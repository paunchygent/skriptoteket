"""Fence each DigiExam workspace import to one document lineage.

Revision ID: d71e4a6c9b20
Revises: d7e4b9a12c80
"""

import sqlalchemy as sa
from alembic import op

revision = "d71e4a6c9b20"
down_revision = "d7e4b9a12c80"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "uq_exam_answer_key_enrichment_jobs_digiexam_import_lineage",
        "exam_answer_key_enrichment_jobs",
        ["workspace_lineage_id"],
        unique=True,
        postgresql_where=sa.text("source_kind = 'digiexam_import'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_exam_answer_key_enrichment_jobs_digiexam_import_lineage",
        table_name="exam_answer_key_enrichment_jobs",
    )
