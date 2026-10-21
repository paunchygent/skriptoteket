"""Retire retired converter ledger rows and the enrichment retry identity.

The signed-in old exam converter stored its runs in the shared
``conversion_hub_jobs`` ledger with ``source_format = 'dxe'`` and
``output_format = 'examnet_bundle'``. Those enum values are gone from
``ConversionHubJob``, so the surviving rows can no longer load. The
document-converter and transcript lanes keep their own rows.

The retired converter's advisory-retry ``retry_identity`` on
``exam_answer_key_enrichment_jobs`` has no producer or consumer, so the
column goes with the rows.

Revision ID: 015a3af12871
Revises: 52f2fe74483a
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "015a3af12871"
down_revision: str | Sequence[str] | None = "52f2fe74483a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_RETIRED_JOB_IDS = (
    "SELECT id FROM conversion_hub_jobs "
    "WHERE source_format = 'dxe' OR output_format = 'examnet_bundle'"
)


def upgrade() -> None:
    """Delete retired converter rows with their dependents; drop retry_identity."""

    op.execute(
        "DELETE FROM conversion_hub_transcript_formatter_export_states "
        f"WHERE conversion_hub_job_id IN ({_RETIRED_JOB_IDS})"
    )
    op.execute(
        "DELETE FROM conversion_hub_transcript_formatter_artifacts "
        f"WHERE conversion_hub_job_id IN ({_RETIRED_JOB_IDS})"
    )
    op.execute(
        "DELETE FROM conversion_hub_saved_transcripts "
        f"WHERE conversion_hub_job_id IN ({_RETIRED_JOB_IDS})"
    )
    op.execute(
        "DELETE FROM conversion_hub_jobs "
        "WHERE source_format = 'dxe' OR output_format = 'examnet_bundle'"
    )

    op.drop_column("exam_answer_key_enrichment_jobs", "retry_identity")


def downgrade() -> None:
    """Restore the retry_identity column; deleted rows are not restored."""

    op.add_column(
        "exam_answer_key_enrichment_jobs",
        sa.Column("retry_identity", sa.String(length=255), nullable=True),
    )
