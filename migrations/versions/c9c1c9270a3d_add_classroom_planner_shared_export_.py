"""add classroom planner shared export webhook binding

Revision ID: c9c1c9270a3d
Revises: b18f6a0d3e2c
Create Date: 2026-03-24 21:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c9c1c9270a3d"
down_revision: Union[str, Sequence[str], None] = "b18f6a0d3e2c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_BINDING_KEY = "classroom-planner-seating-export"


def upgrade() -> None:
    """Upgrade schema."""

    op.create_table(
        "classroom_planner_seating_export_webhook_bindings",
        sa.Column("binding_key", sa.String(length=64), nullable=False),
        sa.Column("subscription_id", sa.String(length=255), nullable=True),
        sa.Column("callback_url", sa.String(length=500), nullable=True),
        sa.Column("secret", sa.String(length=255), nullable=True),
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
        sa.PrimaryKeyConstraint("binding_key"),
    )
    op.execute(
        sa.text(
            """
            INSERT INTO classroom_planner_seating_export_webhook_bindings (
                binding_key,
                subscription_id,
                callback_url,
                secret
            ) VALUES (
                :binding_key,
                NULL,
                NULL,
                NULL
            )
            """
        ).bindparams(binding_key=_BINDING_KEY)
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_table("classroom_planner_seating_export_webhook_bindings")
