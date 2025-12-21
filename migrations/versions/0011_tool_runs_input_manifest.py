from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0011_tool_runs_input_manifest"
down_revision = "0010_curated_apps_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tool_runs",
        sa.Column(
            "input_manifest",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{\"files\":[]}'::jsonb"),
        ),
    )
    op.execute(
        "UPDATE tool_runs SET input_manifest = jsonb_build_object("
        "'files', jsonb_build_array("
        "jsonb_build_object('name', input_filename, 'bytes', input_size_bytes)"
        ")"
        ")"
    )


def downgrade() -> None:
    op.drop_column("tool_runs", "input_manifest")
