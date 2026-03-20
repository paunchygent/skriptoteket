"""create classroom planner roster and room template tables

Revision ID: 57a6ea32ef0a
Revises: 0032_user_file_vault
Create Date: 2026-03-20 19:06:16.356721

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "57a6ea32ef0a"
down_revision: Union[str, Sequence[str], None] = "0032_user_file_vault"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "classroom_planner_room_templates",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("owner_user_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "seats", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False
        ),
        sa.Column(
            "created_at",
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
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_classroom_planner_room_templates_owner_user_id"),
        "classroom_planner_room_templates",
        ["owner_user_id"],
        unique=False,
    )
    op.create_table(
        "classroom_planner_rosters",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("owner_user_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "students", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False
        ),
        sa.Column(
            "created_at",
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
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_classroom_planner_rosters_owner_user_id"),
        "classroom_planner_rosters",
        ["owner_user_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_classroom_planner_rosters_owner_user_id"), table_name="classroom_planner_rosters"
    )
    op.drop_table("classroom_planner_rosters")
    op.drop_index(
        op.f("ix_classroom_planner_room_templates_owner_user_id"),
        table_name="classroom_planner_room_templates",
    )
    op.drop_table("classroom_planner_room_templates")
