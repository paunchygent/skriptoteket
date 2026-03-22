"""allow roomless seating drafts

Revision ID: 91f6c4a7b2d1
Revises: 6b44e9b5d3c1
Create Date: 2026-03-22 15:10:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "91f6c4a7b2d1"
down_revision: Union[str, Sequence[str], None] = "6b44e9b5d3c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.drop_constraint(
        "ck_cp_seating_draft_requires_template",
        "classroom_planner_plan_drafts",
        type_="check",
    )


def downgrade() -> None:
    """Downgrade schema."""

    connection = op.get_bind()
    owner_rows = connection.execute(
        sa.text(
            """
            SELECT DISTINCT owner_user_id
            FROM classroom_planner_plan_drafts
            WHERE draft_kind = 'seating' AND template_id IS NULL
            """
        )
    ).fetchall()

    for row in owner_rows:
        owner_user_id = row[0]
        template_id = connection.execute(
            sa.text(
                """
                SELECT id
                FROM classroom_planner_room_templates
                WHERE owner_user_id = :owner_user_id
                ORDER BY updated_at DESC, created_at DESC, id
                LIMIT 1
                """
            ),
            {"owner_user_id": owner_user_id},
        ).scalar_one_or_none()

        if template_id is None:
            template_id = uuid4()
            connection.execute(
                sa.text(
                    """
                    INSERT INTO classroom_planner_room_templates (
                        id,
                        owner_user_id,
                        name,
                        seats
                    )
                    VALUES (
                        :id,
                        :owner_user_id,
                        :name,
                        CAST(:seats AS jsonb)
                    )
                    """
                ),
                {
                    "id": template_id,
                    "owner_user_id": owner_user_id,
                    "name": "Återställd sal",
                    "seats": "[]",
                },
            )

        connection.execute(
            sa.text(
                """
                UPDATE classroom_planner_plan_drafts
                SET template_id = :template_id
                WHERE owner_user_id = :owner_user_id
                  AND draft_kind = 'seating'
                  AND template_id IS NULL
                """
            ),
            {
                "owner_user_id": owner_user_id,
                "template_id": template_id,
            },
        )

    op.create_check_constraint(
        "ck_cp_seating_draft_requires_template",
        "classroom_planner_plan_drafts",
        "(draft_kind = 'grouping') OR (template_id IS NOT NULL)",
    )
