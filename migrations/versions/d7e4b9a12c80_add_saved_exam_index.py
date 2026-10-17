"""Add the saved exam index and profile ordering preference.

Revision ID: d7e4b9a12c80
Revises: c8a1f7e42d90
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "d7e4b9a12c80"
down_revision = "c8a1f7e42d90"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "exam_index" not in inspector.get_table_names():
        op.create_table(
            "exam_index",
            sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("lineage_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("course_key", sa.String(64), nullable=True),
            sa.Column("title", sa.String(), nullable=False),
            sa.Column("saved_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("head_vault_file_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.PrimaryKeyConstraint("owner_user_id", "lineage_id"),
            sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["head_vault_file_id"], ["user_vault_files.id"], ondelete="CASCADE"
            ),
            sa.UniqueConstraint("head_vault_file_id"),
        )
    if "exam_list_ordering" not in {
        column["name"] for column in inspector.get_columns("user_profiles")
    }:
        op.add_column(
            "user_profiles",
            sa.Column("exam_list_ordering", sa.String(16), nullable=False, server_default="course"),
        )
    # Seed from vault metadata only. Re-running never overwrites a teacher's saved metadata.
    op.execute(
        sa.text("""
        INSERT INTO exam_index
            (owner_user_id, lineage_id, course_key, title, saved_at, head_vault_file_id)
        SELECT DISTINCT ON (user_id, document_lineage_id)
            user_id, document_lineage_id, NULL,
            regexp_replace(name, '(\\.provdokument\\.zip|\\.[^.]+)$', ''),
            document_saved_at, id
        FROM user_vault_files
        WHERE document_lineage_id IS NOT NULL
          AND document_version IS NOT NULL
          AND document_saved_at IS NOT NULL
          AND export_format IS NULL
          AND source_artifact_id LIKE 'documents.conversion_hub:exam-workspace:%'
        ORDER BY user_id, document_lineage_id, (deleted_at IS NULL) DESC,
                 document_version DESC, document_saved_at DESC, id
        ON CONFLICT (owner_user_id, lineage_id) DO NOTHING
    """)
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "exam_index" in inspector.get_table_names():
        op.drop_table("exam_index")
    if "exam_list_ordering" in {
        column["name"] for column in inspector.get_columns("user_profiles")
    }:
        op.drop_column("user_profiles", "exam_list_ordering")
