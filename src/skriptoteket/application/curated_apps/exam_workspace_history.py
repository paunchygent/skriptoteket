"""Persistent editor history, separate from the teacher's saved exam file."""

from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from skriptoteket.application.curated_apps.exam_workspace_export_blockers import (
    NativeDocumentWithExportBlockers,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import NativeExamDocument
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_export_rules import (
    NativeExportBlocker,
)


class ExamWorkspaceHistoryStep(BaseModel):
    model_config = ConfigDict(frozen=True, ser_json_bytes="base64", val_json_bytes="base64")

    step_id: UUID
    content: bytes


MAX_RETAINED_UNDO_STEPS = 100
"""Undo steps kept after the import baseline; older steps fall away on the next store."""


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
    model_config = ConfigDict(frozen=True, extra="forbid")

    expected_cursor: UUID
    document: NativeExamDocument
    after_step_id: UUID | None = None


class MoveExamWorkspaceHistoryPositionRequest(BaseModel):
    """Undo or redo to an already retained snapshot without storing a new step."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    expected_cursor: UUID
    step_id: UUID


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
