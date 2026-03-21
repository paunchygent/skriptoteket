"""classroom planner draft kind and class scoped invariant

Revision ID: 6b44e9b5d3c1
Revises: 9f1a6c4d2e7b
Create Date: 2026-03-22 00:30:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6b44e9b5d3c1"
down_revision: Union[str, Sequence[str], None] = "9f1a6c4d2e7b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "classroom_planner_plan_drafts",
        sa.Column("draft_kind", sa.String(length=32), server_default="seating", nullable=False),
    )
    op.alter_column("classroom_planner_plan_drafts", "template_id", nullable=True)
    op.drop_index("uq_cp_active_draft_owner", table_name="classroom_planner_plan_drafts")
    op.create_check_constraint(
        "ck_cp_seating_draft_requires_template",
        "classroom_planner_plan_drafts",
        "(draft_kind = 'grouping') OR (template_id IS NOT NULL)",
    )
    op.create_index(
        "uq_cp_active_draft_roster_kind",
        "classroom_planner_plan_drafts",
        ["owner_user_id", "roster_id", "draft_kind"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()

    op.drop_index("uq_cp_active_draft_roster_kind", table_name="classroom_planner_plan_drafts")
    op.drop_constraint(
        "ck_cp_seating_draft_requires_template",
        "classroom_planner_plan_drafts",
        type_="check",
    )

    owner_ids = [
        row[0]
        for row in bind.execute(
            sa.text(
                """
                SELECT DISTINCT owner_user_id
                FROM classroom_planner_plan_drafts
                WHERE template_id IS NULL
                """
            )
        ).fetchall()
    ]
    for owner_id in owner_ids:
        placeholder_template_id = str(uuid4())
        bind.execute(
            sa.text(
                """
                INSERT INTO classroom_planner_room_templates (
                    id,
                    owner_user_id,
                    name,
                    seats,
                    fixtures
                )
                VALUES (
                    :id,
                    :owner_user_id,
                    :name,
                    CAST(:seats AS jsonb),
                    CAST(:fixtures AS jsonb)
                )
                """
            ),
            {
                "id": placeholder_template_id,
                "owner_user_id": str(owner_id),
                "name": "Återställd klassrumskontext",
                "seats": "[]",
                "fixtures": "[]",
            },
        )
        bind.execute(
            sa.text(
                """
                UPDATE classroom_planner_plan_drafts
                SET template_id = :template_id
                WHERE owner_user_id = :owner_user_id
                  AND template_id IS NULL
                """
            ),
            {"template_id": placeholder_template_id, "owner_user_id": str(owner_id)},
        )

    op.alter_column("classroom_planner_plan_drafts", "template_id", nullable=False)
    op.drop_column("classroom_planner_plan_drafts", "draft_kind")

    bind.execute(
        sa.text(
            """
            WITH ranked_active_drafts AS (
                SELECT
                    id,
                    ROW_NUMBER() OVER (
                        PARTITION BY owner_user_id
                        ORDER BY
                            last_opened_at DESC NULLS LAST,
                            updated_at DESC NULLS LAST,
                            created_at DESC NULLS LAST,
                            id DESC
                    ) AS active_rank
                FROM classroom_planner_plan_drafts
                WHERE status = 'active'
            )
            UPDATE classroom_planner_plan_drafts AS draft
            SET
                status = 'superseded',
                updated_at = now()
            FROM ranked_active_drafts
            WHERE draft.id = ranked_active_drafts.id
              AND ranked_active_drafts.active_rank > 1
            """
        )
    )
    op.create_index(
        "uq_cp_active_draft_owner",
        "classroom_planner_plan_drafts",
        ["owner_user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )
