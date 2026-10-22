"""Track the current conversion phase and its start time on exam import jobs.

Domain purpose: the DOCX/PDF conversion job reports which step of the import it is in
(reading the file, finding the questions, sorting them by type, converting them) and when
that step started, so the status poll can show a live phase (TASK-SKRIPT-39-04-23 D1).
Both columns are nullable: a job that has reported no phase carries neither.

Revision ID: aa30c309b36c
Revises: 9f3c7a1b4e02
"""

from collections.abc import Sequence

from alembic import op

revision: str = "aa30c309b36c"
down_revision: str | Sequence[str] | None = "9f3c7a1b4e02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the nullable phase and phase-start columns."""

    op.execute(
        "ALTER TABLE exam_answer_key_enrichment_jobs "
        "ADD COLUMN IF NOT EXISTS conversion_phase VARCHAR(16)"
    )
    op.execute(
        "ALTER TABLE exam_answer_key_enrichment_jobs "
        "ADD COLUMN IF NOT EXISTS conversion_phase_started_at TIMESTAMP WITH TIME ZONE"
    )


def downgrade() -> None:
    """Remove the phase and phase-start columns."""

    op.execute(
        "ALTER TABLE exam_answer_key_enrichment_jobs DROP COLUMN IF EXISTS "
        "conversion_phase_started_at"
    )
    op.execute("ALTER TABLE exam_answer_key_enrichment_jobs DROP COLUMN IF EXISTS conversion_phase")
