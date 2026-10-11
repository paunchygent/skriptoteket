"""Source-neutral native exam document for the teacher exam workspace.

Governing decisions: ADR-SKRIPT-0091, ST-SKRIPT-39-04 (S1-S5), EPIC-SKRIPT-39
terms E8-E12. The document is the versioned Mina filer persistence shape. It
reuses exam IR item semantics (item kinds, answer-key provenance vocabulary)
without mirroring source-format internals: there is exactly one body
representation (paragraph segments with inline gap and asset references),
no source type codes, and no source page/line spans.
"""

from __future__ import annotations

import json
import math
from enum import StrEnum
from typing import Annotated, Literal, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from skriptoteket.domain.curated_apps.exam_workspace import native_exam_parent
from skriptoteket.domain.errors import DomainError, ErrorCode

NATIVE_EXAM_DOCUMENT_SCHEMA_VERSION: Literal["native_exam_document_v1"] = "native_exam_document_v1"

NativeExamParent = native_exam_parent.NativeExamParent
parent_points = native_exam_parent.parent_points
_ITEM_ID_PATTERN = r"^item_[0-9]{3,4}$"
_CHOICE_ID_PATTERN = r"^choice_[0-9]{3}$"
_GAP_ID_PATTERN = r"^gap_[0-9]{3}$"
_MATCH_LEFT_ID_PATTERN = r"^left_[0-9]{3}$"
_MATCH_RIGHT_ID_PATTERN = r"^right_[0-9]{3}$"
_ASSET_ID_PATTERN = r"^asset_[0-9a-f]{16}$"
_SHA256_PATTERN = r"^[0-9a-f]{64}$"


class NativeExamItemKind(StrEnum):
    """Writer-proven item subset (EPIC-SKRIPT-39 E3)."""

    FREE_TEXT = "free_text"
    SINGLE_CHOICE = "single_choice"
    MULTIPLE_RESPONSE = "multiple_response"
    GAP_FILL = "gap_fill"
    MATCHING = "matching"


class NativeParseOrigin(StrEnum):
    DETERMINISTIC = "deterministic"
    LLM_PARSED = "llm_parsed"
    TEACHER_CREATED = "teacher_created"


class NativeItemReviewState(StrEnum):
    REVIEW_REQUIRED = "review_required"
    REVIEW_COMPLETE = "review_complete"


class NativeAnswerKeyOrigin(StrEnum):
    """Provenance vocabulary aligned with the exam-conversion review states."""

    ABSENT = "absent"
    NOT_APPLICABLE = "not_applicable"
    SOURCE_PROVIDED = "source_provided"
    TEACHER_AUTHORED = "teacher_authored"
    MACHINE_PROPOSED = "machine_proposed"
    REVIEWED_ADVISORY = "reviewed_advisory"


_TRUSTED_KEY_ORIGINS = frozenset(
    {
        NativeAnswerKeyOrigin.SOURCE_PROVIDED,
        NativeAnswerKeyOrigin.TEACHER_AUTHORED,
        NativeAnswerKeyOrigin.REVIEWED_ADVISORY,
    }
)

_KEYED_KINDS = frozenset(
    {
        NativeExamItemKind.SINGLE_CHOICE,
        NativeExamItemKind.MULTIPLE_RESPONSE,
        NativeExamItemKind.GAP_FILL,
        NativeExamItemKind.MATCHING,
    }
)


class NativeTextSegment(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["text"] = "text"
    text: str = Field(min_length=1)


class NativeGapSegment(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["gap"] = "gap"
    gap_id: str = Field(pattern=_GAP_ID_PATTERN)


class NativeAssetSegment(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["asset"] = "asset"
    asset_id: str = Field(pattern=_ASSET_ID_PATTERN)


NativeSegment = Annotated[
    Union[NativeTextSegment, NativeGapSegment, NativeAssetSegment],
    Field(discriminator="kind"),
]


class NativeParagraph(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    segments: tuple[NativeSegment, ...] = Field(min_length=1)


class NativeChoice(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    choice_id: str = Field(pattern=_CHOICE_ID_PATTERN)
    text: str = Field(min_length=1)


class NativeMatchLeft(BaseModel):
    """One entry of the list the student matches from."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    left_id: str = Field(pattern=_MATCH_LEFT_ID_PATTERN)
    text: str = Field(min_length=1)


class NativeMatchRight(BaseModel):
    """One entry of the list the student matches to."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    right_id: str = Field(pattern=_MATCH_RIGHT_ID_PATTERN)
    text: str = Field(min_length=1)


class NativeMatchPair(BaseModel):
    """One correct directed pair: a left entry and the right entry it matches."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    left_id: str = Field(pattern=_MATCH_LEFT_ID_PATTERN)
    right_id: str = Field(pattern=_MATCH_RIGHT_ID_PATTERN)


class NativeGap(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    gap_id: str = Field(pattern=_GAP_ID_PATTERN)
    accepted_values: tuple[str, ...] = ()
    hint: str | None = None

    @field_validator("accepted_values")
    @classmethod
    def _non_empty_values(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        for value in values:
            if not value.strip():
                raise ValueError("accepted_values entries must be non-empty")
        return values


class NativeAnswerKey(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    origin: NativeAnswerKeyOrigin
    correct_choice_ids: tuple[str, ...] = ()
    match_pairs: tuple[NativeMatchPair, ...] = ()


class NativeItemReview(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    state: NativeItemReviewState
    parse_origin: NativeParseOrigin
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    reasons: tuple[str, ...] = ()


class NativeExamAsset(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    asset_id: str = Field(pattern=_ASSET_ID_PATTERN)
    sha256: str = Field(pattern=_SHA256_PATTERN)
    media_type: Literal["image/png", "image/jpeg"]
    byte_length: int = Field(gt=0)
    width: int | None = Field(default=None, gt=0)
    height: int | None = Field(default=None, gt=0)


class NativeExamDocumentOrigin(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["docx_import", "created"]
    source_filename: str | None = None
    source_sha256: str | None = Field(default=None, pattern=_SHA256_PATTERN)
    extractor_version: str | None = None

    @model_validator(mode="after")
    def _import_requires_source(self) -> "NativeExamDocumentOrigin":
        if self.kind == "docx_import":
            if not self.source_filename or not self.source_sha256:
                raise ValueError("docx_import origin requires source_filename and source_sha256")
        return self


class NativeExamItem(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    item_id: str = Field(pattern=_ITEM_ID_PATTERN)
    sequence: int = Field(ge=1)
    kind: NativeExamItemKind
    title: str | None = None
    printed_label: str | None = None  # "Fråga 3", "a": title metadata only, never shown (D20)
    body: tuple[NativeParagraph, ...] = Field(min_length=1)
    points: int | float | None = None
    choices: tuple[NativeChoice, ...] = ()
    gaps: tuple[NativeGap, ...] = ()
    match_left: tuple[NativeMatchLeft, ...] = ()
    match_right: tuple[NativeMatchRight, ...] = ()
    answer_key: NativeAnswerKey
    marking_guide: str | None = None  # rättningsmall: only free_text carries one (D31)
    review: NativeItemReview
    source_anchor: str | None = None

    @field_validator("points")
    @classmethod
    def _positive_finite_points(cls, points: int | float | None) -> int | float | None:
        if points is None:
            return None
        if isinstance(points, float) and not math.isfinite(points):
            raise ValueError("points must be finite")
        if points <= 0:
            raise ValueError("points must be positive")
        return points

    @model_validator(mode="after")
    def _kind_invariants(self) -> "NativeExamItem":
        choice_ids = [choice.choice_id for choice in self.choices]
        gap_ids = [gap.gap_id for gap in self.gaps]
        if len(set(choice_ids)) != len(choice_ids):
            raise ValueError("choice ids must be unique")
        if len(set(gap_ids)) != len(gap_ids):
            raise ValueError("gap ids must be unique")
        left_ids = [entry.left_id for entry in self.match_left]
        right_ids = [entry.right_id for entry in self.match_right]
        if len(set(left_ids)) != len(left_ids) or len(set(right_ids)) != len(right_ids):
            raise ValueError("match entry ids must be unique")
        if self.kind is not NativeExamItemKind.MATCHING and (self.match_left or self.match_right):
            raise ValueError("only matching items carry match lists")

        if self.kind in (
            NativeExamItemKind.SINGLE_CHOICE,
            NativeExamItemKind.MULTIPLE_RESPONSE,
        ):
            if len(self.choices) < 2:
                raise ValueError("choice items need at least two choices")
            if self.gaps:
                raise ValueError("choice items must not declare gaps")
        elif self.kind is NativeExamItemKind.GAP_FILL:
            if not self.gaps:
                raise ValueError("gap_fill items need at least one gap")
            if self.choices:
                raise ValueError("gap_fill items must not declare choices")
        elif self.kind is NativeExamItemKind.MATCHING:
            if not self.match_left or len(self.match_right) < 2:
                raise ValueError("matching items need left entries and at least two right entries")
            if self.choices or self.gaps:
                raise ValueError("matching items must not declare choices or gaps")
        else:
            if self.choices or self.gaps:
                raise ValueError("free_text items carry no choices or gaps")
        if self.marking_guide and self.kind is not NativeExamItemKind.FREE_TEXT:
            raise ValueError("only free_text items carry a marking guide")

        self._answer_key_invariants(frozenset(choice_ids))
        self._body_gap_invariants(gap_ids)
        return self

    def _answer_key_invariants(self, known_choice_ids: frozenset[str]) -> None:
        key = self.answer_key
        if self.kind is NativeExamItemKind.FREE_TEXT:
            if key.origin is not NativeAnswerKeyOrigin.NOT_APPLICABLE:
                raise ValueError("free_text answer-key origin must be not_applicable")
            if key.correct_choice_ids or key.match_pairs:
                raise ValueError("free_text items carry no answer-key data")
            return
        if key.origin is NativeAnswerKeyOrigin.NOT_APPLICABLE:
            raise ValueError("keyed item kinds cannot use not_applicable origin")

        if key.match_pairs and self.kind is not NativeExamItemKind.MATCHING:
            raise ValueError("only matching items key match pairs")
        has_key_data = (
            bool(key.correct_choice_ids)
            or bool(key.match_pairs)
            or any(gap.accepted_values for gap in self.gaps)
        )
        if key.origin is NativeAnswerKeyOrigin.ABSENT:
            if has_key_data:
                raise ValueError("absent answer key must not carry key data")
            return

        unknown = set(key.correct_choice_ids) - known_choice_ids
        if unknown:
            raise ValueError(f"correct choice ids not declared: {sorted(unknown)}")
        if self.kind is NativeExamItemKind.SINGLE_CHOICE:
            if len(key.correct_choice_ids) != 1:
                raise ValueError("single_choice needs exactly one correct choice")
        elif self.kind is NativeExamItemKind.MULTIPLE_RESPONSE:
            if not key.correct_choice_ids:
                raise ValueError("multiple_response needs at least one correct choice")
        elif self.kind is NativeExamItemKind.MATCHING:
            self._match_pair_invariants(key.match_pairs)
        else:
            if key.correct_choice_ids:
                raise ValueError("gap_fill items key gaps, not choices")
            for gap in self.gaps:
                if not gap.accepted_values:
                    raise ValueError(f"gap {gap.gap_id} needs accepted values for a keyed item")

    def _match_pair_invariants(self, pairs: tuple[NativeMatchPair, ...]) -> None:
        """Every left entry is paired once; unpaired right entries are distractors."""
        if self.answer_key.correct_choice_ids:
            raise ValueError("matching items key pairs, not choices")
        left_ids = {entry.left_id for entry in self.match_left}
        right_ids = {entry.right_id for entry in self.match_right}
        paired_left = [pair.left_id for pair in pairs]
        paired_right = [pair.right_id for pair in pairs]
        if set(paired_left) - left_ids or set(paired_right) - right_ids:
            raise ValueError("match pairs must refer to declared entries")
        if sorted(paired_left) != sorted(left_ids):
            raise ValueError("a keyed matching item pairs every left entry exactly once")
        if len(set(paired_right)) != len(paired_right):
            raise ValueError("a keyed matching item pairs each right entry at most once")

    def _body_gap_invariants(self, gap_ids: list[str]) -> None:
        placed: list[str] = []
        for paragraph in self.body:
            for segment in paragraph.segments:
                if isinstance(segment, NativeGapSegment):
                    placed.append(segment.gap_id)
        if self.kind is not NativeExamItemKind.GAP_FILL:
            if placed:
                raise ValueError("only gap_fill bodies may place gap segments")
            return
        if sorted(placed) != sorted(gap_ids):
            raise ValueError("gap_fill body must place every declared gap exactly once")

    def body_asset_ids(self) -> tuple[str, ...]:
        found: list[str] = []
        for paragraph in self.body:
            for segment in paragraph.segments:
                if isinstance(segment, NativeAssetSegment):
                    found.append(segment.asset_id)
        return tuple(found)

    def plain_text_lines(self) -> tuple[str, ...]:
        """Render body paragraphs to plain text with ``[___]`` gap markers."""
        lines: list[str] = []
        for paragraph in self.body:
            parts: list[str] = []
            for segment in paragraph.segments:
                if isinstance(segment, NativeTextSegment):
                    parts.append(segment.text)
                elif isinstance(segment, NativeGapSegment):
                    parts.append("[___]")
            line = "".join(parts).strip()
            if line:
                lines.append(line)
        return tuple(lines)


class NativeExamDocument(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["native_exam_document_v1"] = NATIVE_EXAM_DOCUMENT_SCHEMA_VERSION
    document_id: UUID
    revision: int = Field(ge=1)
    title: str = Field(min_length=1)
    instructions: tuple[str, ...] = ()
    items: tuple[NativeExamItem, ...] = Field(min_length=1)
    parents: tuple[NativeExamParent, ...] = ()
    assets: tuple[NativeExamAsset, ...] = ()
    origin: NativeExamDocumentOrigin

    @model_validator(mode="after")
    def _document_invariants(self) -> "NativeExamDocument":
        item_ids = [item.item_id for item in self.items]
        if len(set(item_ids)) != len(item_ids):
            raise ValueError("item ids must be unique")
        sequences = [item.sequence for item in self.items]
        if sequences != list(range(1, len(self.items) + 1)):
            raise ValueError("item sequences must be contiguous from 1 in order")

        asset_ids = [asset.asset_id for asset in self.assets]
        if len(set(asset_ids)) != len(asset_ids):
            raise ValueError("asset ids must be unique")
        known_assets = set(asset_ids)
        referenced: set[str] = set()
        for item in self.items:
            for asset_id in item.body_asset_ids():
                if asset_id not in known_assets:
                    raise ValueError(f"item {item.item_id} references unknown asset")
                referenced.add(asset_id)
        orphans = known_assets - referenced
        if orphans:
            raise ValueError(f"unreferenced assets: {sorted(orphans)}")
        native_exam_parent.validate_parent_structure(self.parents, self.items)
        return self

    def parent_of(self, item_id: str) -> NativeExamParent | None:
        return next((parent for parent in self.parents if item_id in parent.item_ids), None)

    def item_by_id(self, item_id: str) -> NativeExamItem:
        for item in self.items:
            if item.item_id == item_id:
                return item
        raise DomainError(
            code=ErrorCode.NOT_FOUND,
            message="Exam item not found.",
            details={"item_id": item_id},
        )


class NativeExportBlocker(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    item_id: str
    reason: Literal[
        "review_required",
        "machine_proposed_key_unreviewed",
        "missing_points",
        "missing_answer_key",
    ]


def native_export_blockers(document: NativeExamDocument) -> tuple[NativeExportBlocker, ...]:
    """S4 gate: LLM output and low-confidence items need review before export.

    Keyed kinds without an answer key block export: Exam.net QTI would carry an
    automatic item with no correct response and the Exam.net PDF prints the key.
    """
    blockers: list[NativeExportBlocker] = []
    for item in document.items:
        if item.review.state is NativeItemReviewState.REVIEW_REQUIRED:
            blockers.append(NativeExportBlocker(item_id=item.item_id, reason="review_required"))
        if item.answer_key.origin is NativeAnswerKeyOrigin.MACHINE_PROPOSED:
            blockers.append(
                NativeExportBlocker(
                    item_id=item.item_id,
                    reason="machine_proposed_key_unreviewed",
                )
            )
        if item.kind in _KEYED_KINDS and item.answer_key.origin is NativeAnswerKeyOrigin.ABSENT:
            blockers.append(NativeExportBlocker(item_id=item.item_id, reason="missing_answer_key"))
        if item.points is None:
            blockers.append(NativeExportBlocker(item_id=item.item_id, reason="missing_points"))
    return tuple(blockers)


def item_has_trusted_key(item: NativeExamItem) -> bool:
    if item.kind not in _KEYED_KINDS:
        return False
    return item.answer_key.origin in _TRUSTED_KEY_ORIGINS


def native_exam_document_json_bytes(document: NativeExamDocument) -> bytes:
    payload = document.model_dump(mode="json")
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def parse_native_exam_document(data: bytes) -> NativeExamDocument:
    try:
        payload = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise DomainError(
            code=ErrorCode.VALIDATION_ERROR,
            message="Native exam document payload is not valid JSON.",
        ) from error
    try:
        return NativeExamDocument.model_validate(payload)
    except ValidationError as error:
        raise DomainError(
            code=ErrorCode.VALIDATION_ERROR,
            message="Native exam document payload failed validation.",
            details={"errors": error.error_count()},
        ) from error
