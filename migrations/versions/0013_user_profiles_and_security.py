from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0013_user_profiles_and_security"
down_revision = "0012_tool_owner_user_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("email_verified", sa.Boolean(), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "failed_login_attempts",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column("users", sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "users",
        sa.Column("last_failed_login_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.execute(sa.text("UPDATE users SET email_verified = true WHERE email_verified IS NULL"))
    op.alter_column(
        "users",
        "email_verified",
        nullable=False,
        server_default="false",
    )

    op.create_table(
        "user_profiles",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=True),
        sa.Column("last_name", sa.String(length=100), nullable=True),
        sa.Column("display_name", sa.String(length=100), nullable=True),
        sa.Column(
            "locale",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'sv-SE'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_user_profiles_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.execute(
        sa.text(
            ""
            "INSERT INTO user_profiles (user_id, locale, created_at, updated_at) "
            "SELECT id, 'sv-SE', now(), now() FROM users"
        )
    )


def downgrade() -> None:
    op.drop_table("user_profiles")
    op.drop_column("users", "last_failed_login_at")
    op.drop_column("users", "last_login_at")
    op.drop_column("users", "locked_until")
    op.drop_column("users", "failed_login_attempts")
    op.drop_column("users", "email_verified")
