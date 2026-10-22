"""Persistent editor history, separate from the teacher's saved exam file."""

from __future__ import annotations

import zlib
from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from skriptoteket.application.curated_apps.exam_workspace_export_blockers import (
    NativeDocumentWithExportBlockers,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import NativeExamDocument
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document_json import (
    native_exam_document_json_bytes,
    parse_native_exam_document,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_export_rules import (
    NativeExportBlocker,
)


class ExamWorkspaceHistoryStep(BaseModel):
    model_config = ConfigDict(frozen=True, ser_json_bytes="base64", val_json_bytes="base64")

    step_id: UUID
    content: bytes


MAX_RETAINED_UNDO_STEPS = 100
"""Undo steps kept after the import baseline; older steps fall away on the next store."""

_STEP_DOCUMENT_COMPRESSION_LEVEL = 6
"""Zlib level for stored step documents; pictures are stored once, uncompressed."""


def dump_step_document(document: NativeExamDocument) -> bytes:
    """The stored bytes of one step: its document JSON without picture bytes, compressed."""
    return zlib.compress(
        native_exam_document_json_bytes(document), _STEP_DOCUMENT_COMPRESSION_LEVEL
    )


def load_step_document(data: bytes) -> NativeExamDocument:
    """Parse stored step bytes back into the step's document, without picture bytes."""
    return parse_native_exam_document(zlib.decompress(data))


class ExamWorkspaceHistoryCursor(BaseModel):
    """One exam's history row: the concurrency cursor and where the editor stands."""

    model_config = ConfigDict(frozen=True)

    cursor: UUID
    current_step_id: UUID
    """The retained snapshot (baseline or step) the editor stands on."""
    baseline_step_id: UUID


class ExamWorkspaceHistoryStoredStep(BaseModel):
    """One stored step row: the step's document without picture bytes.

    ``asset_ids`` projects the document's asset list so picture garbage
    collection never parses step documents; the document stays the source of truth.
    """

    model_config = ConfigDict(frozen=True)

    step_id: UUID
    position: int
    """Append order; the baseline is position 0 and later steps count up."""
    document: NativeExamDocument
    asset_ids: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()


class ExamWorkspaceHistoryStepRef(BaseModel):
    """The ordering and picture references of one stored step, without its document."""

    model_config = ConfigDict(frozen=True)

    step_id: UUID
    position: int
    asset_ids: tuple[str, ...] = ()


def stored_step(
    *, step_id: UUID, position: int, document: NativeExamDocument, notes: tuple[str, ...]
) -> ExamWorkspaceHistoryStoredStep:
    """Build a step row record with the asset projection derived from its document."""
    return ExamWorkspaceHistoryStoredStep(
        step_id=step_id,
        position=position,
        document=document,
        asset_ids=tuple(asset.asset_id for asset in document.assets),
        notes=notes,
    )


class ExamWorkspaceHistoryState(BaseModel):
    model_config = ConfigDict(frozen=True)

    cursor: UUID
    """Concurrency token: rotates on every write, including Spara; never a step to stand on."""
    current_step_id: UUID
    """The retained snapshot (baseline or step) the editor stands on; Spara keeps the
    saved copy retained at it, so the editor never stands outside its history."""
    baseline: ExamWorkspaceHistoryStep
    steps: tuple[ExamWorkspaceHistoryStep, ...] = ()

    @model_validator(mode="after")
    def validate_current_step(self) -> Self:
        if not any(step.step_id == self.current_step_id for step in (self.baseline, *self.steps)):
            raise ValueError("The current editor step must be retained in history.")
        return self

    def current_step(self) -> ExamWorkspaceHistoryStep:
        """The retained snapshot (baseline or step) the editor stands on."""
        return next(
            step for step in (self.baseline, *self.steps) if step.step_id == self.current_step_id
        )


class StoreExamWorkspaceUndoStepRequest(BaseModel):
    model_config = ConfigDict(
        frozen=True, extra="forbid", ser_json_bytes="base64", val_json_bytes="base64"
    )

    expected_cursor: UUID
    document: NativeExamDocument
    new_assets_by_id: dict[str, bytes] = Field(
        default_factory=dict,
        description=(
            "Bytes of pictures this document declares that the server may not hold yet, "
            "sent once by the editor that added them."
        ),
    )
    after_step_id: UUID | None = None
    tab_id: UUID
    """The editing tab's id; the server refuses a store from a tab without the lease."""


class MoveExamWorkspaceHistoryPositionRequest(BaseModel):
    """Undo or redo to an already retained snapshot without storing a new step."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    expected_cursor: UUID
    step_id: UUID
    tab_id: UUID
    """The editing tab's id; the server refuses a move from a tab without the lease."""


class ExamWorkspaceEditLease(BaseModel):
    """One editing tab's server lease, stored next to the exam's history head."""

    model_config = ConfigDict(frozen=True)

    holder_tab_id: UUID | None = None
    renewed_at: datetime | None = None
    takeover_requested_by: UUID | None = None


class ExamWorkspaceEditLeaseRequest(BaseModel):
    """One lease operation for the calling tab: claim, renew, takeover or release."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    tab_id: UUID


class ExamWorkspaceEditLeaseResponse(BaseModel):
    """The lease after one operation; the holder renews while a waiter is named."""

    model_config = ConfigDict(frozen=True)

    holder_tab_id: UUID | None
    renewed_at: datetime | None
    takeover_requested_by: UUID | None
    takeover_requested: bool
    """Whether another tab waits for the lease; the holder stores and releases."""


class SaveAsExamWorkspaceDocumentRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    document: NativeExamDocument


class ExamWorkspaceHistoryResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    cursor: UUID
    baseline_step_id: UUID
    step_ids: tuple[UUID, ...]
    position_step_id: UUID


class ExamWorkspaceHistoryDocumentResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    step_id: UUID
    document: NativeExamDocument


class ExamWorkspaceUndoStepResponse(NativeDocumentWithExportBlockers):
    model_config = ConfigDict(frozen=True)

    history: ExamWorkspaceHistoryResponse

    # Defaulted like the shared base (a ``mode="before"`` validator always fills
    # it, so call sites never pass it), with the stored step's verdict
    # description, so the serialization schema keeps the computed field's shape.
    export_blockers: tuple[NativeExportBlocker, ...] = Field(
        default=(),
        description=(
            "The export gate's verdict on the stored step, for the workspace's blocker rows."
        ),
        json_schema_extra={"readOnly": True},
    )


def history_response(history: ExamWorkspaceHistoryState) -> ExamWorkspaceHistoryResponse:
    return ExamWorkspaceHistoryResponse(
        cursor=history.cursor,
        baseline_step_id=history.baseline.step_id,
        step_ids=tuple(step.step_id for step in history.steps),
        position_step_id=history.current_step_id,
    )


def history_response_for(
    *, head: ExamWorkspaceHistoryCursor, refs: list[ExamWorkspaceHistoryStepRef]
) -> ExamWorkspaceHistoryResponse:
    """Build the history response from the head row and ordered step references."""
    return ExamWorkspaceHistoryResponse(
        cursor=head.cursor,
        baseline_step_id=head.baseline_step_id,
        step_ids=tuple(ref.step_id for ref in refs if ref.step_id != head.baseline_step_id),
        position_step_id=head.current_step_id,
    )
