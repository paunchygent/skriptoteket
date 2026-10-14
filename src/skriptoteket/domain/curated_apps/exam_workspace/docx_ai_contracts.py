"""Producer contract for batched DOCX construction and its diagnostics."""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeExamItemKind,
)


class _Produced(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ProducedSegment(_Produced):
    """One run of student-visible text, one blank the student fills in, or one source picture."""

    kind: Literal["text", "gap", "asset"]
    text: str | None = Field(
        description="The student-visible source wording for a text segment, without any "
        "inline facit answer or label; null for a gap or asset segment."
    )
    accepted_values: tuple[str, ...] = Field(
        description="For a gap: the accepted answers from the teacher's facit, including "
        "facit written inline in the question paragraph. Empty for text and asset."
    )
    asset_id: str | None = Field(
        default=None,
        pattern=r"^asset_[0-9a-f]{16}$",
        description="For an asset: the id of one source picture, copied exactly from its "
        '<image asset_id="..."/> marker at the same place in the body. Null otherwise.',
    )

    @model_validator(mode="after")
    def _kind_fields(self) -> "ProducedSegment":
        if self.kind == "text":
            if not self.text or self.accepted_values or self.asset_id is not None:
                raise ValueError("text segments carry non-empty text only")
        elif self.kind == "gap":
            if self.text is not None or self.asset_id is not None:
                raise ValueError("gap segments carry no text or asset")
        elif self.text is not None or self.accepted_values or not self.asset_id:
            raise ValueError("asset segments carry one asset id only")
        return self


class ProducedParagraph(_Produced):
    segments: tuple[ProducedSegment, ...] = Field(min_length=1)


class ProducedChoice(_Produced):
    text: str = Field(
        min_length=1, description="The option wording without its source letter or number."
    )
    correct: bool = Field(description="True only when the teacher's facit keys this option.")


class ProducedMatchPair(_Produced):
    left: str = Field(description="A match_left entry, copied exactly.")
    right: str = Field(description="The match_right entry the facit pairs it with, copied exactly.")


class ProducedItem(_Produced):
    """One exam question as the model builds it from its source chunks."""

    source_anchors: tuple[str, ...] = Field(
        min_length=1,
        description="Anchors of the question's own chunks: prompt, options and blanks. "
        "Never an answer-key chunk.",
    )
    outcome: Literal["converted", "review", "type_conflict"] = Field(
        description="review when the question cannot be converted faithfully; type_conflict "
        "when the question's response type is not one of the batch's item kinds."
    )
    conflict_kind: NativeExamItemKind | None = Field(
        default=None,
        description="For type_conflict: the item kind the source shows. Null otherwise.",
    )
    review_reason: str | None = Field(
        description="For review: a short Swedish reason naming what blocks conversion. "
        "Null when converted or type_conflict."
    )
    # Strict schemas reject keywords beside a $ref; each request narrows kind to its batch.
    kind: NativeExamItemKind
    printed_label: str | None = Field(
        default=None,
        description="The question's own number or letter as the source prints it, with its "
        'word and without punctuation or points, such as "Fråga 3", "Question 4", "3" '
        'or "a"; null when the source prints none. Never part of the body.',
    )
    body: tuple[ProducedParagraph, ...] = Field(
        min_length=1,
        description="Student-visible question text, also for review items. Inline facit "
        "answers never go into text.",
    )
    points: int | None = Field(description="Points printed in the source, else null.")
    choices: tuple[ProducedChoice, ...] = Field(
        description="Options in source order for single_choice and multiple_response; "
        "empty otherwise."
    )
    match_left: tuple[str, ...] = Field(
        default=(),
        description="For matching: the entries the student matches from, in source order, "
        "without their numbers or letters; empty otherwise.",
    )
    match_right: tuple[str, ...] = Field(
        default=(),
        description="For matching: every entry the student chooses among, in source order, "
        "including entries no pair uses, without their numbers or letters; empty otherwise.",
    )
    match_pairs: tuple[ProducedMatchPair, ...] = Field(
        default=(),
        description="For matching: each pair the teacher's facit keys, one pair per match_left "
        "entry; a match_right entry no pair uses stays in match_right. Empty without a facit "
        "entry and for other kinds.",
    )
    marking_guide: str | None = Field(
        default=None,
        description="For free_text: the teacher's marking guide for the question (sample "
        "answer, grading criteria or points guidance) copied from the facit wording; null "
        "when the facit gives none and for other kinds.",
    )

    @model_validator(mode="after")
    def _pairs_name_entries(self) -> "ProducedItem":
        for pair in self.match_pairs:
            if pair.left not in self.match_left or pair.right not in self.match_right:
                raise ValueError("each match pair copies one match_left and one match_right entry")
        return self


class ProducedMetadata(_Produced):
    text: str = Field(min_length=1)
    source_anchors: tuple[str, ...] = Field(min_length=1)
    points: int | None = Field(
        default=None,
        description="For an instruction: the total its line prints for a section or a group "
        "of questions. Null for the title, the exam's overall total and lines without points.",
    )


class DocxBuildEnvelope(_Produced):
    """The strict output the provider is required to return."""

    title: ProducedMetadata | None
    instructions: tuple[ProducedMetadata, ...]
    answer_key_anchors: tuple[str, ...] = Field(
        description="Anchors of chunks that hold the teacher's facit or answers."
    )
    items: tuple[ProducedItem, ...]


DocxBuildStage = Literal[
    "provider", "admission", "fallback", "job", "grouping", "labeling", "batch", "assembly"
]


class DocxBuildEvent(_Produced):
    """One observed failure in a DOCX build, free of exam wording."""

    stage: DocxBuildStage
    code: str
    batch: str | None = None
    item: int | None = None
    anchors: tuple[str, ...] = ()
    detail: str = ""

    def as_json(self) -> dict[str, JsonValue]:
        return self.model_dump(mode="json")


@dataclass(frozen=True)
class DocxStageTiming:
    """Wall-clock seconds of one pipeline stage, measured from conversion start."""

    stage: str
    started_seconds: float
    finished_seconds: float


@dataclass(frozen=True)
class DocxBuildResult:
    document: NativeExamDocument
    notes: tuple[str, ...]
    input_tokens: int | None = None
    output_tokens: int | None = None
    events: tuple[DocxBuildEvent, ...] = ()
    timings: tuple[DocxStageTiming, ...] = ()
    assets_by_id: Mapping[str, bytes] = MappingProxyType({})
