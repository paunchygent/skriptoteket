"""Add domain allowlist tables.

Revision ID: 5a7c1d9e3b2f
Revises: 4d2c6b8e1a9f
Create Date: 2026-03-30 00:45:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "5a7c1d9e3b2f"
down_revision = "4d2c6b8e1a9f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "allowed_domains",
        sa.Column("domain", sa.String(length=255), nullable=False),
        sa.Column("org_type", sa.String(length=64), nullable=False),
        sa.Column("org_name", sa.String(length=255), nullable=False),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("source_ref", sa.String(length=500), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("domain"),
    )
    op.create_index(
        op.f("ix_allowed_domains_org_type"),
        "allowed_domains",
        ["org_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_allowed_domains_is_active"),
        "allowed_domains",
        ["is_active"],
        unique=False,
    )

    op.create_table(
        "blocked_domains",
        sa.Column("domain", sa.String(length=255), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("source_ref", sa.String(length=500), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("domain"),
    )
    op.create_index(
        op.f("ix_blocked_domains_is_active"),
        "blocked_domains",
        ["is_active"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_blocked_domains_is_active"), table_name="blocked_domains")
    op.drop_table("blocked_domains")

    op.drop_index(op.f("ix_allowed_domains_is_active"), table_name="allowed_domains")
    op.drop_index(op.f("ix_allowed_domains_org_type"), table_name="allowed_domains")
    op.drop_table("allowed_domains")
