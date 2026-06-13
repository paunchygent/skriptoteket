"""Add transcript formatter artifact content payloads.

Domain purpose:
  Persist Gateway-authorized transcript formatter artifact bytes next to their
  Sir Convert producer refs so download and Mina filer save actions do not
  require a later direct producer read.

Relationships:
  - Extends `conversion_hub_transcript_formatter_artifacts`.
  - Backed by `ConversionHubTranscriptFormatterArtifactModel.content`.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e9a4b6c8d2f0"
down_revision: str | None = "e1f2a3b4c5d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "conversion_hub_transcript_formatter_artifacts",
        sa.Column("content", sa.LargeBinary(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("conversion_hub_transcript_formatter_artifacts", "content")
