"""Producer contract for batched DOCX construction and its diagnostics."""

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeExamItemKind,
)


class _Produced(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ProducedSegment(_Produced):
    """One run of student-visible text, or one blank the student fills in."""

    kind: Literal["text", "gap"]
    text: str | None = Field(
        description="The student-visible source wording for a text segment, without any "
        "inline facit answer or label; null for a gap segment."
    )
    accepted_values: tuple[str, ...] = Field(
        description="For a gap: the accepted answers from the teacher's facit, including "
        "facit written inline in the question paragraph. Empty for text."
    )
    hint: str | None = Field(
        description="Always null: a cue printed beside a blank is student-visible text in "
        "the text segment after the gap."
    )

    @model_validator(mode="after")
    def _kind_fields(self) -> "ProducedSegment":
        if self.kind == "text" and (self.text is None or self.accepted_values or self.hint):
            raise ValueError("text segments carry text only")
        if self.kind == "gap" and self.text is not None:
            raise ValueError("gap segments carry no text")
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
    outcome: Literal["converted", "review"] = Field(
        description="review when the question cannot be converted faithfully."
    )
    review_reason: str | None = Field(
        description="For review: a short Swedish reason naming what blocks conversion. "
        "Null when converted."
    )
    kind: NativeExamItemKind
    title: str | None = Field(description="A question heading printed in the source, else null.")
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


DocxBuildStage = Literal["provider", "admission", "fallback", "job"]


class DocxBuildEvent(_Produced):
    """One observed failure in a DOCX build, free of exam wording."""

    stage: DocxBuildStage
    code: str
    round: int | None = None
    item: int | None = None
    anchors: tuple[str, ...] = ()
    detail: str = ""

    def as_json(self) -> dict[str, JsonValue]:
        return self.model_dump(mode="json")


@dataclass(frozen=True)
class DocxBuildResult:
    document: NativeExamDocument
    notes: tuple[str, ...]
    input_tokens: int | None = None
    output_tokens: int | None = None
    events: tuple[DocxBuildEvent, ...] = ()
