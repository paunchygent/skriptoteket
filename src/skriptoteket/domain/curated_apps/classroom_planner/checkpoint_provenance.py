"""Checkpoint provenance values for classroom-planner Smart history.

Purpose:
    Describe which durable teacher action created a Smart-history checkpoint so
    seating and grouping history can accept both explicit exports and
    authenticated share artifacts without conflating their persistence models.

Relationships:
    - Used by seating and grouping checkpoint domain models.
    - Mirrored by checkpoint ORM rows and Alembic provenance constraints.
"""

from __future__ import annotations

from enum import StrEnum


class CheckpointSourceKind(StrEnum):
    """Identify the durable action that produced one checkpoint."""

    EXPORT_JOB = "export_job"
    SHARE_ARTIFACT = "share_artifact"
