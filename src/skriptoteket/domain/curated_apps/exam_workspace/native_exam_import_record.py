"""Original exam wording and ordered, typed import decisions for one question."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
)


class NativeExamOriginalWording(BaseModel):
    """Source wording kept independently of later teacher edits."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        json_schema_serialization_defaults_required=True,
    )

    question_text: str
    answer_key_text: str | None


class NativeExamChosenTypeStep(BaseModel):
    """The question type selected at import."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        json_schema_serialization_defaults_required=True,
    )

    kind: Literal["chosen_type"] = "chosen_type"
    chosen_kind: NativeExamItemKind


class NativeExamAnswerKeyStep(BaseModel):
    """Where the answer key came from at import."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        json_schema_serialization_defaults_required=True,
    )

    kind: Literal["answer_key"] = "answer_key"
    origin: NativeAnswerKeyOrigin


class NativeExamRetryStep(BaseModel):
    """One recorded type-conflict resend or teacher-requested retry."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        json_schema_serialization_defaults_required=True,
    )

    kind: Literal["retry"] = "retry"
    reason: Literal["type_conflict", "teacher_request"]
    from_kind: NativeExamItemKind
    chosen_kind: NativeExamItemKind
    outcome: Literal["converted", "review_required"]


NativeExamImportStep = Annotated[
    NativeExamChosenTypeStep | NativeExamAnswerKeyStep | NativeExamRetryStep,
    Field(discriminator="kind"),
]


class NativeExamImportRecord(BaseModel):
    """Original wording followed by the import decisions and any later retries."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        json_schema_serialization_defaults_required=True,
    )

    original_wording: NativeExamOriginalWording
    steps: tuple[NativeExamImportStep, ...]

    @model_validator(mode="after")
    def _ordered_steps(self) -> "NativeExamImportRecord":
        if len(self.steps) < 2:
            raise ValueError(
                "import steps require a chosen_type step followed by an answer_key step"
            )
        if not isinstance(self.steps[0], NativeExamChosenTypeStep):
            raise ValueError("the first import step must be chosen_type")
        if not isinstance(self.steps[1], NativeExamAnswerKeyStep):
            raise ValueError("the second import step must be answer_key")
        if any(not isinstance(step, NativeExamRetryStep) for step in self.steps[2:]):
            raise ValueError(
                "only retry steps may follow the initial chosen_type and answer_key steps"
            )
        return self
