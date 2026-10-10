"""Source-bound provider contracts for batched DOCX construction."""

from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeExamItem,
)


class SourceText(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    text: str = Field(min_length=1)
    source_anchors: tuple[str, ...] = Field(min_length=1)


class SourceEvidence(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    anchor: str
    text: str = Field(min_length=1)


class KeyEvidence(SourceEvidence):
    target_id: str
    value: str = Field(min_length=1)


class DocxBuildEntry(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    item: NativeExamItem
    source_anchors: tuple[str, ...] = Field(min_length=1)
    question_label: str = Field(min_length=1)
    points_evidence: SourceEvidence | None
    key_evidence: tuple[KeyEvidence, ...]


class DocxBuildEnvelope(BaseModel):
    """Provider shape; entries are validated separately at admission."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    title: SourceText | None
    instructions: tuple[SourceText, ...]
    items: tuple[DocxBuildEntry, ...]


@dataclass(frozen=True)
class DocxBuildResult:
    document: NativeExamDocument
    notes: tuple[str, ...]
    input_tokens: int | None = None
    output_tokens: int | None = None
