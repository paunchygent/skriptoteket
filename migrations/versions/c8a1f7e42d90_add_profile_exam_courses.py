"""Store the teacher's school forms and ordered exam catalog keys.

Revision ID: c8a1f7e42d90
Revises: 4e9b7d1c6a02
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "c8a1f7e42d90"
down_revision = "4e9b7d1c6a02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_profiles",
        sa.Column(
            "exam_courses",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text('\'{"school_forms": [], "course_keys": []}\'::jsonb'),
        ),
    )


def downgrade() -> None:
    op.drop_column("user_profiles", "exam_courses")
