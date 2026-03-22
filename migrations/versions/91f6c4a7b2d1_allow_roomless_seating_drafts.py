"""allow roomless seating drafts

Revision ID: 91f6c4a7b2d1
Revises: 6b44e9b5d3c1
Create Date: 2026-03-22 15:10:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union

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

    op.create_check_constraint(
        "ck_cp_seating_draft_requires_template",
        "classroom_planner_plan_drafts",
        "(draft_kind = 'grouping') OR (template_id IS NOT NULL)",
    )
