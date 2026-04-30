"""repair share artifact lifecycle foreign keys

Revision ID: b4c6d8e1f2a3
Revises: a8f5c7d9e2b1
Create Date: 2026-04-30 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b4c6d8e1f2a3"
down_revision: Union[str, Sequence[str], None] = "a8f5c7d9e2b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE = "classroom_planner_share_artifacts"
_LEGACY_DRAFT_FK = "classroom_planner_share_artifacts_draft_id_fkey"
_LEGACY_OWNER_FK = "classroom_planner_share_artifacts_owner_user_id_fkey"
_DRAFT_FK = "fk_cp_share_artifacts_draft_id"
_OWNER_FK = "fk_cp_share_artifacts_owner_user_id"


def upgrade() -> None:
    """Remove database-owned cascade deletion from immutable share provenance."""

    op.drop_constraint(_LEGACY_DRAFT_FK, _TABLE, type_="foreignkey")
    op.drop_constraint(_LEGACY_OWNER_FK, _TABLE, type_="foreignkey")
    op.create_foreign_key(
        _DRAFT_FK,
        _TABLE,
        "classroom_planner_plan_drafts",
        ["draft_id"],
        ["id"],
    )
    op.create_foreign_key(
        _OWNER_FK,
        _TABLE,
        "users",
        ["owner_user_id"],
        ["id"],
    )


def downgrade() -> None:
    """Restore the original cascade behavior for revision rollback."""

    op.drop_constraint(_DRAFT_FK, _TABLE, type_="foreignkey")
    op.drop_constraint(_OWNER_FK, _TABLE, type_="foreignkey")
    op.create_foreign_key(
        _LEGACY_DRAFT_FK,
        _TABLE,
        "classroom_planner_plan_drafts",
        ["draft_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        _LEGACY_OWNER_FK,
        _TABLE,
        "users",
        ["owner_user_id"],
        ["id"],
        ondelete="CASCADE",
    )
