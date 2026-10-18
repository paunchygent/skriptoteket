"""Producer contract for batched DOCX construction and its diagnostics."""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator, model_validator

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    IMPORTABLE_ITEM_KINDS,
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
        description="For a gap: correct answer forms from the teacher's facit, including "
        "inline facit, or proposed answers when the item's key_source is invented. "
        "Empty for text and asset."
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
    correct: bool = Field(
        description="True when this option is keyed by the teacher's facit, or by the "
        "proposed key when the item's key_source is invented."
    )


class ProducedMatchPair(_Produced):
    left: str = Field(description="A match_left entry, copied exactly.")
    right: str = Field(
        description="The match_right entry the key pairs it with, copied exactly. "
        "The item's key_source states whether that key came from facit or was invented."
    )


class ProducedCriterion(_Produced):
    """One grading criterion the answer key states for a free_text question (Q12)."""

    text: str = Field(
        min_length=1,
        description="One criterion's wording, copied from the answer key without its points "
        "or facit label; never student-visible text.",
    )
    points: int | float | None = Field(
        default=None,
        description="For a criterion the answer key states points for: its whole points, at "
        "least 1, copied from the key; never computed or split. Null when the key states no "
        "per-criterion points, which only one criterion holding the whole guide may be.",
    )

    @model_validator(mode="after")
    def _text_has_wording(self) -> "ProducedCriterion":
        if not self.text.strip():
            raise ValueError("a criterion's text must contain the answer key's wording")
        return self


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
    key_source: Literal["copied", "interpreted", "invented"] | None = Field(
        description="copied: the facit's own answer words, including a letter mapped to "
        "its choice or listed alternatives split. interpreted: answers extracted from "
        "a facit sentence or matching pairs inferred from prose. invented: solved without "
        "a facit entry. Null when there is no objective key or for free_text."
    )
    facit_text: str | None = Field(
        description="The teacher's original facit wording for this question, copied "
        "verbatim, including inline answers. Null only when this question has no facit entry."
    )
    points: int | float | None = Field(
        description="Points printed in the source, else null. A fractional printed point stays "
        "as printed; conversion sends a free_text item whose points cannot be whole criteria "
        "to needs review."
    )
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
        description="For matching: every tick the teacher's facit keys, one pair per tick. "
        "Every match_left entry appears in at least one pair and a match_right entry may "
        "serve several pairs or none; the same pair never appears twice. A proposed key "
        "without a facit entry uses key_source invented. Empty for other kinds.",
    )
    criteria: tuple[ProducedCriterion, ...] = Field(
        default=(),
        description="For free_text: the grading criteria the answer key states, in order, each "
        "with the points the key states for it. Exactly one criterion with points null when "
        "the key gives a guide without per-criterion points, holding the whole guide; empty "
        "when the facit gives no guidance and for every other kind.",
    )

    @field_validator("kind", "conflict_kind")
    @classmethod
    def _importable_kind(cls, value: NativeExamItemKind | None) -> NativeExamItemKind | None:
        if value is not None and value not in IMPORTABLE_ITEM_KINDS:
            raise ValueError("an import never produces ordering questions")
        return value

    @model_validator(mode="after")
    def _pairs_name_entries(self) -> "ProducedItem":
        if self.facit_text is not None and not self.facit_text.strip():
            raise ValueError("facit_text must contain the teacher's wording")
        # Admission builds only a converted reply; a review or type_conflict reply gives only
        # its anchors, reason and kind, so its key fields cannot reject it.
        if self.outcome != "converted":
            return self
        if self.key_source in {"copied", "interpreted"} and self.facit_text is None:
            raise ValueError("a facit-derived key requires facit_text")
        if self.key_source == "invented" and self.facit_text is not None:
            raise ValueError("an invented key has no facit entry")
        keyed = (
            any(choice.correct for choice in self.choices)
            or bool(self.match_pairs)
            or any(s.accepted_values for p in self.body for s in p.segments if s.kind == "gap")
        )
        if self.kind is NativeExamItemKind.FREE_TEXT:
            if self.key_source is not None:
                raise ValueError("free_text has no objective key source")
        elif keyed != (self.key_source is not None):
            raise ValueError("each objective key states its source; an empty key has none")
        for pair in self.match_pairs:
            if pair.left not in self.match_left or pair.right not in self.match_right:
                raise ValueError("each match pair copies one match_left and one match_right entry")
        pairs = {(pair.left, pair.right) for pair in self.match_pairs}
        if len(pairs) != len(self.match_pairs):
            raise ValueError("a matching key states each pair at most once")
        if self.match_pairs and {pair.left for pair in self.match_pairs} != set(self.match_left):
            raise ValueError("a matching key names every match_left entry at least once")

        if self.criteria and self.kind is not NativeExamItemKind.FREE_TEXT:
            raise ValueError("only free_text items carry criteria")
        if any(criterion.points is None for criterion in self.criteria) and len(self.criteria) != 1:
            raise ValueError("a guide without per-criterion points is one criterion")
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
    "provider",
    "admission",
    "fallback",
    "job",
    "grouping",
    "labeling",
    "batch",
    "assembly",
    "formatting",
]


class DocxBuildEvent(_Produced):
    """One observed build diagnostic or typography path, free of exam wording."""

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
