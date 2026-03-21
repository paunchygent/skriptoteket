"""classroom planner single active draft invariant

Revision ID: d8f0d0ef2b6d
Revises: c2a6b2f4d91e
Create Date: 2026-03-21 21:05:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d8f0d0ef2b6d"
down_revision: Union[str, Sequence[str], None] = "c2a6b2f4d91e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
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
    op.create_index(
        "uq_cp_active_draft_owner",
        "classroom_planner_plan_drafts",
        ["owner_user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("uq_cp_active_draft_owner", table_name="classroom_planner_plan_drafts")
