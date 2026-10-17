"""Native exam item shape, cross-field invariants and body projections."""

from __future__ import annotations

import math
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeAssetSegment,
    NativeGapSegment,
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_criteria import (
    NativeExamCriterion,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_import_record import (
    NativeExamImportRecord,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_matching import (
    NativeMatchLeft,
    NativeMatchRight,
    validate_matching_pairs,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_retry_records import (
    NativeExamRetrySource,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_suggestions import (
    validate_answer_key_suggestion,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKey,
    NativeAnswerKeySuggestion,
    NativeChoice,
    NativeGap,
    NativeItemReview,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    ITEM_ID_PATTERN,
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
)


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
    # One uniform non-negative two-decimal tick value per grid; never default saved grids.
    tick_points: Decimal | None = Field(default=None, ge=0, decimal_places=2, allow_inf_nan=False)
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
    # Source wording and import-time decisions, independent of subsequent teacher edits.
    import_record: NativeExamImportRecord | None = None

    @field_validator("points", mode="before")
    @classmethod
    def _nonnegative_finite_points(cls, points: object) -> int | float | None:
        if points is None:
            return None
        if isinstance(points, bool) or not isinstance(points, (int, float)):
            raise ValueError("points must be a number")
        if isinstance(points, float) and not math.isfinite(points):
            raise ValueError("points must be finite")
        if points < 0:
            raise ValueError("points must be non-negative")
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
        elif self.kind in (NativeExamItemKind.GAP_FILL, NativeExamItemKind.INLINE_CHOICE):
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
        self._gap_options_invariants()
        self._criteria_invariants()

        self._answer_key_invariants(frozenset(choice_ids))
        self._tick_points_invariants()
        validate_answer_key_suggestion(self.ai_suggestion)
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
            or any(gap.accepted_values or gap.correct_option_id for gap in self.gaps)
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
            validate_matching_pairs(
                key.match_pairs, self.match_left, self.match_right, key.correct_choice_ids
            )
        else:
            if key.correct_choice_ids:
                raise ValueError("gap_fill items key gaps, not choices")
            for gap in self.gaps:
                if self.kind is NativeExamItemKind.INLINE_CHOICE:
                    continue
                if not gap.accepted_values:
                    raise ValueError(f"gap {gap.gap_id} needs accepted values for a keyed item")

    def _gap_options_invariants(self) -> None:
        for gap in self.gaps:
            if self.kind is not NativeExamItemKind.INLINE_CHOICE:
                if gap.options or gap.correct_option_id is not None:
                    raise ValueError("only inline_choice gaps carry options and an option key")
                continue
            if gap.accepted_values or gap.automatic_values or gap.excluded_automatic_values:
                raise ValueError("inline_choice gaps must not carry typed accepted values")
            option_ids = [option.choice_id for option in gap.options]
            if not option_ids:
                raise ValueError("inline_choice gaps need an option list")
            if len(set(option_ids)) != len(option_ids):
                raise ValueError("gap option ids must be unique within the gap")
            if gap.correct_option_id is None or gap.correct_option_id not in option_ids:
                raise ValueError("inline_choice gaps need exactly one correct option in their list")

    def _tick_points_invariants(self) -> None:
        """One uniform tick value per grid: points are exactly tick value × ticks (T2).

        A matching item always carries ``tick_points`` and a stored document is never
        defaulted, so an item saved under the old one-to-one rule fails validation. With
        no key there are no ticks, so only absent or zero points agree with the
        derived total. A zero tick value makes a keyed grid worth zero points.
        """

        if self.kind is not NativeExamItemKind.MATCHING:
            if self.tick_points is not None:
                raise ValueError("only matching items carry tick_points")
            return
        if self.tick_points is None:
            raise ValueError("matching items need a tick_points value")
        ticks = len(self.answer_key.match_pairs)
        if self.points is None:
            if ticks:
                raise ValueError("matching points must equal tick_points times the number of pairs")
            return
        if Decimal(str(self.points)) != self.tick_points * ticks:
            raise ValueError("matching points must equal tick_points times the number of pairs")

    def _body_gap_invariants(self, gap_ids: list[str]) -> None:
        placed: list[str] = []
        for paragraph in self.body:
            for segment in paragraph.segments:
                if isinstance(segment, NativeGapSegment):
                    placed.append(segment.gap_id)
        if self.kind not in (NativeExamItemKind.GAP_FILL, NativeExamItemKind.INLINE_CHOICE):
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

    def body_gaps(self) -> tuple[NativeGap, ...]:
        """Declared gaps in their validated body placement order."""
        gaps = {gap.gap_id: gap for gap in self.gaps}
        return tuple(
            gaps[segment.gap_id]
            for paragraph in self.body
            for segment in paragraph.segments
            if isinstance(segment, NativeGapSegment)
        )

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
