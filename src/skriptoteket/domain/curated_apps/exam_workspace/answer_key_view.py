"""Neutral answer-key item views for native exam workspace enrichment.

Purpose:
    Project keyed native exam items into a source-neutral view the machine
    answer-key completion line can prompt from, validate one provider
    decision back into a typed proposal, and turn a proposal into the AI
    suggestion kept on the question (TASK-SKRIPT-39-04-07), and fingerprint
    the question's answer-relevant content to report a kept suggestion out
    of date. The editor decides when a suggestion becomes the key; saving
    the document validates that key against its question.

Relationships:
    - Consumed by ``domain.curated_apps.exam_workspace.answer_key_prompts``
      and by the workspace branch of
      ``application.curated_apps.handlers.exam_answer_key_enrichment_jobs``.
    - Mirrors the decision-validation semantics of
      ``domain.curated_apps.exam_conversion.digiexam_answer_key_completion``.
"""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import TypeGuard

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeGapSegment,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_matching import (
    NativeMatchPair,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import (
    NativeExamParent,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKeySuggestion,
    NativeGapAcceptedValues,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_plain_text


class AnswerKeyViewKind(StrEnum):
    """Keyed item kinds the completion line can propose keys for."""

    CHOICE = "choice"
    MULTI = "multi"
    GAP_FILL = "gap_fill"
    MATCHING = "matching"


_VIEW_KIND_BY_ITEM_KIND: dict[NativeExamItemKind, AnswerKeyViewKind] = {
    NativeExamItemKind.SINGLE_CHOICE: AnswerKeyViewKind.CHOICE,
    NativeExamItemKind.MULTIPLE_RESPONSE: AnswerKeyViewKind.MULTI,
    NativeExamItemKind.GAP_FILL: AnswerKeyViewKind.GAP_FILL,
    NativeExamItemKind.MATCHING: AnswerKeyViewKind.MATCHING,
}


class AnswerKeyItemView(BaseModel):
    """Source-neutral prompt projection of one unkeyed native exam item."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    item_id: str
    kind: AnswerKeyViewKind
    # The instruction a grouped question's parent prints above it, such as a word bank.
    instruction: str = ""
    stem_text: str
    choices: tuple[tuple[int, str], ...] = ()
    gap_count: int = Field(default=0, ge=0)
    gap_ids: tuple[str, ...] = ()
    cloze_text: str = ""
    match_left: tuple[tuple[int, str], ...] = ()
    match_right: tuple[tuple[int, str], ...] = ()

    @model_validator(mode="after")
    def _kind_invariants(self) -> AnswerKeyItemView:
        if self.gap_count != len(self.gap_ids):
            raise ValueError("gap_count must match the number of gap ids")
        if self.kind is AnswerKeyViewKind.GAP_FILL:
            if not self.gap_ids or self.choices or self.match_left or self.match_right:
                raise ValueError("gap_fill views carry gaps and no choices or match lists")
        elif self.kind is AnswerKeyViewKind.MATCHING:
            if not self.match_left or len(self.match_right) < 2 or self.choices or self.gap_ids:
                raise ValueError(
                    "matching views carry left entries, at least two right entries, "
                    "and no choices or gaps"
                )
        else:
            if len(self.choices) < 2 or self.gap_ids or self.match_left or self.match_right:
                raise ValueError("choice views need at least two choices and no gaps or matches")
        return self


class AnswerKeyItemProposal(BaseModel):
    """One validated machine answer-key proposal for a native exam item."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    item_id: str
    kind: AnswerKeyViewKind
    correct_choice_ids: tuple[str, ...] = ()
    gap_accepted_values: tuple[tuple[str, tuple[str, ...]], ...] = ()
    match_pairs: tuple[tuple[str, str], ...] = ()


def choice_int_id(choice_id: str) -> int:
    """Map a native ``choice_NNN`` id to its integer prompt id."""

    return int(choice_id.removeprefix("choice_"))


def native_choice_id(int_id: int) -> str:
    """Map an integer prompt id back to the native ``choice_NNN`` id."""

    if int_id < 0:
        raise ValueError("choice ids cannot be negative")
    return f"choice_{int_id:03d}"


def match_int_id(entry_id: str) -> int:
    """Map a native ``left_NNN`` or ``right_NNN`` id to its integer prompt id."""

    return int(entry_id.rpartition("_")[2])


def native_left_id(int_id: int) -> str:
    """Map an integer prompt id back to the native ``left_NNN`` id."""

    if int_id < 0:
        raise ValueError("match ids cannot be negative")
    return f"left_{int_id:03d}"


def native_right_id(int_id: int) -> str:
    """Map an integer prompt id back to the native ``right_NNN`` id."""

    if int_id < 0:
        raise ValueError("match ids cannot be negative")
    return f"right_{int_id:03d}"


def _gap_ids_in_body_order(item: NativeExamItem) -> tuple[str, ...]:
    placed: list[str] = []
    for paragraph in item.body:
        for segment in paragraph.segments:
            if isinstance(segment, NativeGapSegment):
                placed.append(segment.gap_id)
    return tuple(placed)


def _numbered_cloze_text(item: NativeExamItem, gap_ids: tuple[str, ...]) -> str:
    """Render body paragraphs with numbered ``[n]`` gap markers in body order.

    Mirrors what the DigiExam gap prompt derives from ``<span dx-wg-id>``
    markers: one number per gap in reading order, whitespace collapsed,
    empty lines dropped.
    """

    numbers = {gap_id: index for index, gap_id in enumerate(gap_ids, start=1)}
    lines: list[str] = []
    for paragraph in item.body:
        parts: list[str] = []
        for segment in paragraph.segments:
            if isinstance(segment, NativeTextSegment):
                parts.append(segment.text)
            elif isinstance(segment, NativeGapSegment):
                parts.append(f" [{numbers[segment.gap_id]}] ")
        line = " ".join("".join(parts).split())
        if line:
            lines.append(_remove_space_before_punctuation(line))
    return "\n".join(lines)


def _remove_space_before_punctuation(text: str) -> str:
    result = text
    for mark in (".", ",", ":", ";", "?", "!"):
        result = result.replace(f" {mark}", mark)
    return result


def answer_key_item_view(
    item: NativeExamItem, parent: NativeExamParent | None
) -> AnswerKeyItemView:
    """Project one keyed native exam item, under its parent's instruction, into its prompt view."""

    kind = _VIEW_KIND_BY_ITEM_KIND.get(item.kind)
    if kind is None:
        raise ValueError(f"Item kind {item.kind.value} carries no answer key.")
    gap_ids = _gap_ids_in_body_order(item)
    return AnswerKeyItemView(
        item_id=item.item_id,
        kind=kind,
        instruction=body_plain_text(parent.instruction) if parent else "",
        stem_text="\n".join(item.plain_text_lines()),
        choices=tuple((choice_int_id(choice.choice_id), choice.text) for choice in item.choices),
        gap_count=len(gap_ids),
        gap_ids=gap_ids,
        cloze_text=(
            _numbered_cloze_text(item, gap_ids) if kind is AnswerKeyViewKind.GAP_FILL else ""
        ),
        match_left=tuple((match_int_id(entry.left_id), entry.text) for entry in item.match_left),
        match_right=tuple((match_int_id(entry.right_id), entry.text) for entry in item.match_right),
    )


def answer_key_item_views(document: NativeExamDocument) -> tuple[AnswerKeyItemView, ...]:
    """Select keyed items whose answer key is absent, in document order."""

    return tuple(
        answer_key_item_view(item, document.parent_of(item.item_id))
        for item in document.items
        if item.kind in _VIEW_KIND_BY_ITEM_KIND
        and item.answer_key.origin is NativeAnswerKeyOrigin.ABSENT
    )


def answer_key_fingerprint_for_view(view: AnswerKeyItemView) -> str:
    """Fingerprint the answer-relevant content one suggestion was made for.

    Covers exactly the fields the answer-key view defines as answer-relevant:
    the kind, the question text (stem and numbered cloze), the choices, the
    gap ids, both match lists and the parent instruction. Titles, points,
    marking guides, review state and the answer key itself are excluded, so
    editing any of those never marks a suggestion out of date.
    """

    payload = {
        "kind": view.kind.value,
        "instruction": view.instruction,
        "stem_text": view.stem_text,
        "cloze_text": view.cloze_text,
        "choices": [list(choice) for choice in view.choices],
        "gap_ids": list(view.gap_ids),
        "match_left": [list(entry) for entry in view.match_left],
        "match_right": [list(entry) for entry in view.match_right],
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def answer_key_fingerprint(item: NativeExamItem, parent: NativeExamParent | None) -> str:
    """Fingerprint one item's current answer-relevant content."""

    return answer_key_fingerprint_for_view(answer_key_item_view(item, parent))


def suggestion_is_outdated(item: NativeExamItem, parent: NativeExamParent | None) -> bool:
    """Report whether the kept suggestion no longer matches the question."""

    if item.ai_suggestion is None:
        return False
    if item.kind not in _VIEW_KIND_BY_ITEM_KIND:
        # A suggestion is only made for a keyed kind; a question changed to
        # a kind without a key has no answer-relevant view left to match.
        return True
    return item.ai_suggestion.fingerprint != answer_key_fingerprint(item, parent)


def proposal_from_model_content(
    *,
    view: AnswerKeyItemView,
    content: dict[str, JsonValue],
) -> AnswerKeyItemProposal | None:
    """Return a validated proposal from one provider decision, or None."""

    if view.kind is AnswerKeyViewKind.GAP_FILL:
        return _validated_gap_proposal(view=view, content=content)
    if view.kind is AnswerKeyViewKind.MATCHING:
        return _validated_matching_proposal(view=view, content=content)
    return _validated_choice_proposal(view=view, content=content)


def _validated_choice_proposal(
    *,
    view: AnswerKeyItemView,
    content: dict[str, JsonValue],
) -> AnswerKeyItemProposal | None:
    ids = _int_tuple(content.get("correct_alternative_ids"))
    if not ids or len(set(ids)) != len(ids):
        return None
    valid_ids = {int_id for int_id, _text in view.choices}
    if any(int_id not in valid_ids for int_id in ids):
        return None
    if view.kind is AnswerKeyViewKind.CHOICE and len(ids) != 1:
        return None
    return AnswerKeyItemProposal(
        item_id=view.item_id,
        kind=view.kind,
        correct_choice_ids=tuple(native_choice_id(int_id) for int_id in ids),
    )


def _validated_gap_proposal(
    *,
    view: AnswerKeyItemView,
    content: dict[str, JsonValue],
) -> AnswerKeyItemProposal | None:
    gap_id_lookup = {gap_id.casefold() for gap_id in view.gap_ids}
    accepted: list[tuple[str, tuple[str, ...]]] = []
    for index, gap_id in enumerate(view.gap_ids, start=1):
        value = content.get(str(index))
        if not isinstance(value, str) or not value.strip():
            return None
        stripped_value = value.strip()
        if stripped_value.casefold() in gap_id_lookup:
            return None
        accepted.append((gap_id, (stripped_value,)))
    if len(accepted) != len(view.gap_ids):
        return None
    return AnswerKeyItemProposal(
        item_id=view.item_id,
        kind=view.kind,
        gap_accepted_values=tuple(accepted),
    )


def _validated_matching_proposal(
    *,
    view: AnswerKeyItemView,
    content: dict[str, JsonValue],
) -> AnswerKeyItemProposal | None:
    """Accept a many-to-many key: every left entry at least once, each pair once.

    A right entry may serve several left entries or none, and a left entry may
    take several right entries; only an undeclared entry, an uncovered left
    entry or a repeated pair is rejected.
    """

    entries = content.get("pairs")
    if not isinstance(entries, list | tuple):
        return None
    pairs: list[tuple[int, int]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            return None
        left_id = entry.get("left_id")
        right_id = entry.get("right_id")
        if not _is_int(left_id) or not _is_int(right_id):
            return None
        pairs.append((left_id, right_id))
    declared_left_ids = {left_id for left_id, _text in view.match_left}
    declared_right_ids = {right_id for right_id, _text in view.match_right}
    if {left_id for left_id, _right_id in pairs} != declared_left_ids:
        return None
    if not {right_id for _left_id, right_id in pairs} <= declared_right_ids:
        return None
    if len(set(pairs)) != len(pairs):
        return None
    return AnswerKeyItemProposal(
        item_id=view.item_id,
        kind=view.kind,
        match_pairs=tuple(
            (native_left_id(left_id), native_right_id(right_id)) for left_id, right_id in pairs
        ),
    )


def _is_int(value: JsonValue | None) -> TypeGuard[int]:
    return isinstance(value, int) and not isinstance(value, bool)


def _int_tuple(value: JsonValue | None) -> tuple[int, ...]:
    if not isinstance(value, list | tuple):
        return ()
    integers: list[int] = []
    for entry in value:
        if not _is_int(entry):
            return ()
        integers.append(entry)
    return tuple(integers)


def suggestion_from_proposal(
    *,
    view: AnswerKeyItemView,
    proposal: AnswerKeyItemProposal,
    provider_profile_id: str,
    model: str,
    prompt_template_version: str,
) -> NativeAnswerKeySuggestion:
    """Turn one validated provider proposal into the suggestion kept on the item."""

    return NativeAnswerKeySuggestion(
        correct_choice_ids=proposal.correct_choice_ids,
        match_pairs=tuple(
            NativeMatchPair(left_id=left_id, right_id=right_id)
            for left_id, right_id in proposal.match_pairs
        ),
        gap_accepted_values=tuple(
            NativeGapAcceptedValues(gap_id=gap_id, accepted_values=values)
            for gap_id, values in proposal.gap_accepted_values
        ),
        fingerprint=answer_key_fingerprint_for_view(view),
        provider_profile_id=provider_profile_id,
        model=model,
        prompt_template_version=prompt_template_version,
    )
