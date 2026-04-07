"""Application contracts for Klassrumskartan public direct-download exports.

Purpose:
    Define the typed request and direct-download response models used by the
    public guest export boundary so anonymous export routes can stay thin.

Relationships:
    - Reuses the browser-owned guest snapshot payload from
      `guest_upgrade_contracts.py`.
    - Consumed by the public grouping and seating export handlers and routes.
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, model_validator

from skriptoteket.application.curated_apps.classroom_planner.exports import (
    GroupingExportKind,
    GroupingExportPaperSize,
    SeatingExportKind,
    SeatingExportLayoutId,
    SeatingExportPaperSize,
)
from skriptoteket.application.curated_apps.classroom_planner.guest_upgrade_contracts import (
    ClassroomPlannerGuestSnapshotPayload,
)


class PublicGroupingExportRequest(BaseModel):
    """Describe one public grouping export request from a guest snapshot."""

    model_config = ConfigDict(frozen=True)

    snapshot: ClassroomPlannerGuestSnapshotPayload
    expected_revision: int
    export_kind: GroupingExportKind
    paper_size: GroupingExportPaperSize | None = None

    @model_validator(mode="after")
    def validate_export_shape(self) -> "PublicGroupingExportRequest":
        """Require the same grouping export contract enforced by auth routes."""

        if self.export_kind is GroupingExportKind.PDF:
            if self.paper_size is None:
                raise ValueError("PDF-export kräver pappersstorlek.")
            if self.paper_size is not GroupingExportPaperSize.A4_PORTRAIT:
                raise ValueError("PDF-export stöder bara A4 stående i den här versionen.")
            return self
        if self.paper_size is not None:
            raise ValueError("Excel-export använder inte pappersstorlek.")
        return self


class PublicSeatingExportRequest(BaseModel):
    """Describe one public seating export request from a guest snapshot."""

    model_config = ConfigDict(frozen=True)

    snapshot: ClassroomPlannerGuestSnapshotPayload
    expected_revision: int
    export_kind: SeatingExportKind
    layout_id: SeatingExportLayoutId | None = None
    paper_size: SeatingExportPaperSize | None = None

    @model_validator(mode="after")
    def validate_export_shape(self) -> "PublicSeatingExportRequest":
        """Require the same seating export contract enforced by auth routes."""

        if self.export_kind is SeatingExportKind.PDF:
            if self.layout_id is None or self.paper_size is None:
                raise ValueError("PDF-export kräver layout och pappersstorlek.")
            return self
        if self.layout_id is not None or self.paper_size is not None:
            raise ValueError("Excel-export använder inte layout eller pappersstorlek.")
        return self


@dataclass(frozen=True, slots=True)
class PublicExportDownload:
    """Describe one in-memory direct-download artifact for a public export."""

    filename: str
    media_type: str
    content: bytes
