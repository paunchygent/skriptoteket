"""Persistent editor history, separate from the teacher's saved exam file."""

from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import NativeExamDocument


class ExamWorkspaceHistoryStep(BaseModel):
    model_config = ConfigDict(frozen=True, ser_json_bytes="base64", val_json_bytes="base64")

    step_id: UUID
    content: bytes


class ExamWorkspaceHistoryState(BaseModel):
    model_config = ConfigDict(frozen=True)

    cursor: UUID
    """Concurrency token: rotates on every write, including Spara; never a step to stand on."""
    current_step_id: UUID | None
    """The retained snapshot (baseline or step) the editor stands on; None when the
    editor stands on a saved document that no retained snapshot holds."""
    baseline: ExamWorkspaceHistoryStep
    steps: tuple[ExamWorkspaceHistoryStep, ...] = ()

    @model_validator(mode="after")
    def validate_current_step(self) -> Self:
        if self.current_step_id is not None and not any(
            step.step_id == self.current_step_id for step in (self.baseline, *self.steps)
        ):
            raise ValueError("The current editor step must be retained in history.")
        return self


class StoreExamWorkspaceUndoStepRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    expected_cursor: UUID
    document: NativeExamDocument
    after_step_id: UUID | None = None


class SaveAsExamWorkspaceDocumentRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    document: NativeExamDocument


class ExamWorkspaceHistoryResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    cursor: UUID
    baseline_step_id: UUID
    step_ids: tuple[UUID, ...]
    position_step_id: UUID | None


class ExamWorkspaceHistoryDocumentResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    step_id: UUID
    document: NativeExamDocument


class ExamWorkspaceUndoStepResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    document: NativeExamDocument
    history: ExamWorkspaceHistoryResponse


def history_response(history: ExamWorkspaceHistoryState) -> ExamWorkspaceHistoryResponse:
    return ExamWorkspaceHistoryResponse(
        cursor=history.cursor,
        baseline_step_id=history.baseline.step_id,
        step_ids=tuple(step.step_id for step in history.steps),
        position_step_id=history.current_step_id,
    )
