"""Source-neutral native exam document for the teacher exam workspace.

Governing decisions: ADR-SKRIPT-0091, ST-SKRIPT-39-04 (S1-S5), EPIC-SKRIPT-39
terms E8-E12. The document is the versioned Mina filer persistence shape. It
reuses exam IR item semantics (item kinds, answer-key provenance vocabulary)
without mirroring source-format internals: there is exactly one body
representation (paragraph segments with inline gap and asset references),
no source type codes, and no source page/line spans.
"""

from __future__ import annotations

import math
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator

from skriptoteket.domain.curated_apps.exam_workspace import native_exam_parent
from skriptoteket.domain.curated_apps.exam_workspace.answer_spelling import (
    filter_answer_spelling_candidates,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeAssetSegment,
    NativeGapSegment,
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeSegment as NativeSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_retry_records import (
    NativeExamRetryChunk as NativeExamRetryChunk,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_retry_records import (
    NativeExamRetryImage as NativeExamRetryImage,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_retry_records import (
    NativeExamRetryMissingImage as NativeExamRetryMissingImage,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_retry_records import (
    NativeExamRetrySource,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    ASSET_ID_PATTERN,
    CHOICE_ID_PATTERN,
    GAP_ID_PATTERN,
    ITEM_ID_PATTERN,
    MATCH_LEFT_ID_PATTERN,
    MATCH_RIGHT_ID_PATTERN,
    SHA256_PATTERN,
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
    NativeItemReviewState,
    NativeParseOrigin,
)
from skriptoteket.domain.errors import DomainError, ErrorCode

NATIVE_EXAM_DOCUMENT_SCHEMA_VERSION: Literal["native_exam_document_v2"] = "native_exam_document_v2"

NativeExamParent = native_exam_parent.NativeExamParent
parent_points = native_exam_parent.parent_points


class NativeChoice(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    choice_id: str = Field(pattern=CHOICE_ID_PATTERN)
    text: str = Field(min_length=1)


class NativeMatchLeft(BaseModel):
    """One entry of the list the student matches from."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    left_id: str = Field(pattern=MATCH_LEFT_ID_PATTERN)
    text: str = Field(min_length=1)


class NativeMatchRight(BaseModel):
    """One entry of the list the student matches to."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    right_id: str = Field(pattern=MATCH_RIGHT_ID_PATTERN)
    text: str = Field(min_length=1)


class NativeMatchPair(BaseModel):
    """One correct directed pair: a left entry and the right entry it matches."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    left_id: str = Field(pattern=MATCH_LEFT_ID_PATTERN)
    right_id: str = Field(pattern=MATCH_RIGHT_ID_PATTERN)


class NativeGap(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        json_schema_serialization_defaults_required=True,
    )

    gap_id: str = Field(pattern=GAP_ID_PATTERN)
    accepted_values: tuple[str, ...] = ()
    automatic_values: tuple[str, ...] = ()

    @field_validator("accepted_values")
    @classmethod
    def _non_empty_values(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        for value in values:
            if not value.strip():
                raise ValueError("accepted_values entries must be non-empty")
        return values

    @field_validator("automatic_values")
    @classmethod
    def _bounded_automatic_values(
        cls, values: tuple[str, ...], info: ValidationInfo
    ) -> tuple[str, ...]:
        """Keep only bounded spellings of an accepted value; drop the rest at save (D7).

        The saved document is normalized, never rejected: a value outside the A10
        distance, a duplicate of an accepted value, or a fourth spelling of one
        accepted value is dropped, and an accepted value's removal drops the
        automatic values that depended on it in the same save.
        """
        accepted = info.data.get("accepted_values") or ()
        return filter_answer_spelling_candidates(accepted, values)


class NativeAnswerKey(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    origin: NativeAnswerKeyOrigin
    correct_choice_ids: tuple[str, ...] = ()
    match_pairs: tuple[NativeMatchPair, ...] = ()


class NativeGapAcceptedValues(BaseModel):
    """The accepted values one AI suggestion proposes for one gap."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    gap_id: str = Field(pattern=GAP_ID_PATTERN)
    accepted_values: tuple[str, ...] = Field(min_length=1)

    @field_validator("accepted_values")
    @classmethod
    def _non_empty_values(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        for value in values:
            if not value.strip():
                raise ValueError("accepted_values entries must be non-empty")
        return values


class NativeAnswerKeySuggestion(BaseModel):
    """One AI answer-key suggestion kept on its question (TASK-SKRIPT-39-04-07).

    Holds the proposed key, a SHA-256 fingerprint of the question's
    answer-relevant content when the suggestion was made, and the provider
    lineage that produced it. It lives apart from the item's answer key so
    it survives the teacher accepting or replacing that key.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    correct_choice_ids: tuple[str, ...] = ()
    match_pairs: tuple[NativeMatchPair, ...] = ()
    gap_accepted_values: tuple[NativeGapAcceptedValues, ...] = ()
    fingerprint: str = Field(pattern=SHA256_PATTERN)
    provider_profile_id: str = Field(min_length=1)
    model: str = Field(min_length=1)
    prompt_template_version: str = Field(min_length=1)


class NativeItemReview(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    state: NativeItemReviewState
    parse_origin: NativeParseOrigin
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    reasons: tuple[str, ...] = ()


class NativeExamAsset(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    asset_id: str = Field(pattern=ASSET_ID_PATTERN)
    sha256: str = Field(pattern=SHA256_PATTERN)
    media_type: Literal["image/png", "image/jpeg"]
    byte_length: int = Field(gt=0)
    width: int | None = Field(default=None, gt=0)
    height: int | None = Field(default=None, gt=0)


class NativeExamDocumentOrigin(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["docx_import", "created"]
    source_filename: str | None = None
    source_sha256: str | None = Field(default=None, pattern=SHA256_PATTERN)
    extractor_version: str | None = None

    @model_validator(mode="after")
    def _import_requires_source(self) -> "NativeExamDocumentOrigin":
        if self.kind == "docx_import":
            if not self.source_filename or not self.source_sha256:
                raise ValueError("docx_import origin requires source_filename and source_sha256")
        return self


class NativeExamCriterion(BaseModel):
    """One Fritext rubric criterion: its text and its whole points (Q12)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str = Field(min_length=1)
    points: int = Field(ge=1)

    @field_validator("points", mode="before")
    @classmethod
    def _whole_points_not_bool(cls, points: object) -> object:
        if isinstance(points, bool):
            raise ValueError("criterion points must be a whole number")
        return points

    @field_validator("text")
    @classmethod
    def _non_empty_text(cls, text: str) -> str:
        if not text.strip():
            raise ValueError("criterion text must be non-empty")
        return text


class NativeExamItem(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        json_schema_serialization_defaults_required=True,
    )

    item_id: str = Field(pattern=ITEM_ID_PATTERN)
    sequence: int = Field(ge=1)
    kind: NativeExamItemKind
    printed_label: str | None = None  # "Fråga 3", "a": printed metadata only, never shown (D20)
    facit_text: str | None = None  # the teacher's original facit wording, kept after undo (D2)
    body: tuple[NativeParagraph, ...] = Field(min_length=1)
    points: int | float | None = None
    # Points no source stated per question: a printed section total split over its
    # questions (D6), or a prose marking guide's single-criterion estimate (R14).
    points_estimated: bool = False
    choices: tuple[NativeChoice, ...] = ()
    gaps: tuple[NativeGap, ...] = ()
    match_left: tuple[NativeMatchLeft, ...] = ()
    match_right: tuple[NativeMatchRight, ...] = ()
    answer_key: NativeAnswerKey
    ai_suggestion: NativeAnswerKeySuggestion | None = None
    # Rubric criteria: only free_text carries any (Q12); their points are the item's.
    criteria: tuple[NativeExamCriterion, ...] = ()
    review: NativeItemReview
    source_anchor: str | None = None
    # The question's original conversion source, when a DOCX conversion built it; it is
    # what one-question retry reads, never the item's current content (D1).
    retry_source: NativeExamRetrySource | None = None

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
        if self.points_estimated and self.points is None:
            raise ValueError("estimated points require points")
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
        self._criteria_invariants()

        self._answer_key_invariants(frozenset(choice_ids))
        self._suggestion_invariants()
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

    def _suggestion_invariants(self) -> None:
        """Check the kept suggestion's own shape, never its currency.

        A suggestion is historical data for the question its fingerprint
        describes: after an answer-relevant edit — including a change of
        the question's kind — it may propose a key for another kind, name
        choices, match entries or gaps the question no longer declares,
        and it stays stored so the fingerprint can report it out of date.
        Only the suggestion's own shape is invariant here: exactly one
        payload family carries the proposed key (choice ids, match pairs
        or gap accepted values) and no entry is named twice within it.
        Producer validation against the requested question and the current
        answer key's constraints live in their own checks, so a stored
        historical suggestion never becomes a valid active key by storage.
        """

        suggestion = self.ai_suggestion
        if suggestion is None:
            return
        families = (
            bool(suggestion.correct_choice_ids),
            bool(suggestion.match_pairs),
            bool(suggestion.gap_accepted_values),
        )
        if sum(families) != 1:
            raise ValueError("a kept suggestion proposes exactly one kind of key")
        if len(set(suggestion.correct_choice_ids)) != len(suggestion.correct_choice_ids):
            raise ValueError("suggested choice ids must be unique")
        paired_left = [pair.left_id for pair in suggestion.match_pairs]
        if len(set(paired_left)) != len(paired_left):
            raise ValueError("a suggestion pairs each left entry at most once")
        paired_right = [pair.right_id for pair in suggestion.match_pairs]
        if len(set(paired_right)) != len(paired_right):
            raise ValueError("a suggestion pairs each right entry at most once")
        suggested_gap_ids = [entry.gap_id for entry in suggestion.gap_accepted_values]
        if len(set(suggested_gap_ids)) != len(suggested_gap_ids):
            raise ValueError("a suggestion names each gap at most once")

    def _match_pair_invariants(self, pairs: tuple[NativeMatchPair, ...]) -> None:
        """Every left entry is paired once; unpaired right entries are distractors."""
        if self.answer_key.correct_choice_ids:
            raise ValueError("matching items key pairs, not choices")
        self._match_pairs_valid(pairs)

    def _match_pairs_valid(self, pairs: tuple[NativeMatchPair, ...]) -> None:
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

    def _criteria_invariants(self) -> None:
        """Fritext-only rubric criteria whose points are exactly the item's points (Q12).

        The list replaces the marking-guide text: every other kind carries none,
        and a non-empty list can never disagree with the item's own points.
        """

        if self.kind is not NativeExamItemKind.FREE_TEXT:
            if self.criteria:
                raise ValueError("only free_text items carry criteria")
            return
        if not self.criteria:
            return
        criteria_points = sum(criterion.points for criterion in self.criteria)
        if self.points != criteria_points:
            raise ValueError("free_text criteria points must equal the item's points")

    def body_asset_ids(self) -> tuple[str, ...]:
        found: list[str] = []
        for paragraph in self.body:
            for segment in paragraph.segments:
                if isinstance(segment, NativeAssetSegment):
                    found.append(segment.asset_id)
        return tuple(found)

    def source_asset_ids(self) -> tuple[str, ...]:
        """Pictures the stored retry source references, teacher-only ones included.

        A picture only the question's facit or read-only context carries is still part of
        its reconvertible source, so it stays a declared, referenced asset; the student body
        and every export read ``body_asset_ids`` instead, so such a picture never reaches
        the QTI package.
        """
        source = self.retry_source
        if source is None:
            return ()
        records = (*source.chunks, *source.key_chunks, *source.context_chunks)
        return tuple(dict.fromkeys(image.asset_id for record in records for image in record.images))

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

    schema_version: Literal["native_exam_document_v2"] = NATIVE_EXAM_DOCUMENT_SCHEMA_VERSION
    document_id: UUID
    revision: int = Field(ge=1)
    title: str = Field(min_length=1)
    instructions: tuple[NativeParagraph, ...] = ()
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
            for asset_id in (*item.body_asset_ids(), *item.source_asset_ids()):
                if asset_id not in known_assets:
                    raise ValueError(f"item {item.item_id} references unknown asset")
                referenced.add(asset_id)
        shared_bodies = (self.instructions, *(parent.instruction for parent in self.parents))
        for body in shared_bodies:
            for paragraph in body:
                for segment in paragraph.segments:
                    if isinstance(segment, NativeGapSegment):
                        raise ValueError("shared instructions cannot contain response gaps")
                    if isinstance(segment, NativeAssetSegment):
                        if segment.asset_id not in known_assets:
                            raise ValueError("shared instructions reference unknown asset")
                        referenced.add(segment.asset_id)
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
