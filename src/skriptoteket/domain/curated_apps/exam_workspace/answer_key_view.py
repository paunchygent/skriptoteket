"""Neutral answer-key item views for native exam workspace enrichment.

Purpose:
    Project keyed native exam items whose answer key is absent into a
    source-neutral view the machine answer-key completion line can prompt
    from, validate one provider decision back into a typed proposal, and
    apply a proposal as an advisory MACHINE_PROPOSED prefill that stays
    behind teacher review. Applying a proposal builds the editor prefill
    payload only; it never mutates a saved document revision.

Relationships:
    - Consumed by ``domain.curated_apps.exam_workspace.answer_key_prompts``
      and by the workspace branch of
      ``application.curated_apps.handlers.exam_answer_key_enrichment_jobs``.
    - Mirrors the decision-validation semantics of
      ``domain.curated_apps.exam_conversion.digiexam_answer_key_completion``.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeAnswerKey,
    NativeAnswerKeyOrigin,
    NativeExamDocument,
    NativeExamItem,
    NativeExamItemKind,
    NativeGapSegment,
    NativeItemReviewState,
    NativeTextSegment,
)
from skriptoteket.domain.errors import DomainError, ErrorCode

EXAM_WORKSPACE_ANSWER_KEY_PROPOSALS_SCHEMA_VERSION: Literal[
    "exam_workspace_answer_key_proposals_v1"
] = "exam_workspace_answer_key_proposals_v1"

MACHINE_PROPOSED_ANSWER_KEY_REVIEW_REASON = "machine_proposed_answer_key"


class AnswerKeyViewKind(StrEnum):
    """Keyed item kinds the completion line can propose keys for."""

    CHOICE = "choice"
    MULTI = "multi"
    GAP_FILL = "gap_fill"


_VIEW_KIND_BY_ITEM_KIND: dict[NativeExamItemKind, AnswerKeyViewKind] = {
    NativeExamItemKind.SINGLE_CHOICE: AnswerKeyViewKind.CHOICE,
    NativeExamItemKind.MULTIPLE_RESPONSE: AnswerKeyViewKind.MULTI,
    NativeExamItemKind.GAP_FILL: AnswerKeyViewKind.GAP_FILL,
}


class AnswerKeyItemView(BaseModel):
    """Source-neutral prompt projection of one unkeyed native exam item."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    item_id: str
    kind: AnswerKeyViewKind
    title: str
    stem_text: str
    choices: tuple[tuple[int, str], ...] = ()
    gap_count: int = Field(default=0, ge=0)
    gap_ids: tuple[str, ...] = ()
    cloze_text: str = ""

    @model_validator(mode="after")
    def _kind_invariants(self) -> AnswerKeyItemView:
        if self.gap_count != len(self.gap_ids):
            raise ValueError("gap_count must match the number of gap ids")
        if self.kind is AnswerKeyViewKind.GAP_FILL:
            if not self.gap_ids or self.choices:
                raise ValueError("gap_fill views carry gaps and no choices")
        else:
            if len(self.choices) < 2 or self.gap_ids:
                raise ValueError("choice views need at least two choices and no gaps")
        return self


class AnswerKeyItemProposal(BaseModel):
    """One validated machine answer-key proposal for a native exam item."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    item_id: str
    kind: AnswerKeyViewKind
    correct_choice_ids: tuple[str, ...] = ()
    gap_accepted_values: tuple[tuple[str, tuple[str, ...]], ...] = ()


class WorkspaceAnswerKeyProposalRecord(BaseModel):
    """One persisted proposal item with its provider candidate lineage."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    item_id: str
    kind: AnswerKeyViewKind
    correct_choice_ids: tuple[str, ...] = ()
    gap_accepted_values: dict[str, tuple[str, ...]] = {}
    provider_profile_id: str
    model: str
    prompt_template_version: str


class WorkspaceAnswerKeyProposalsPayload(BaseModel):
    """Persisted native-shaped proposals payload for one document revision."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["exam_workspace_answer_key_proposals_v1"] = (
        EXAM_WORKSPACE_ANSWER_KEY_PROPOSALS_SCHEMA_VERSION
    )
    lineage_id: UUID
    document_revision: int = Field(ge=1)
    items: tuple[WorkspaceAnswerKeyProposalRecord, ...] = Field(min_length=1)


def choice_int_id(choice_id: str) -> int:
    """Map a native ``choice_NNN`` id to its integer prompt id."""

    return int(choice_id.removeprefix("choice_"))


def native_choice_id(int_id: int) -> str:
    """Map an integer prompt id back to the native ``choice_NNN`` id."""

    if int_id < 0:
        raise ValueError("choice ids cannot be negative")
    return f"choice_{int_id:03d}"


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


def answer_key_item_view(item: NativeExamItem) -> AnswerKeyItemView:
    """Project one keyed native exam item into its prompt view."""

    kind = _VIEW_KIND_BY_ITEM_KIND.get(item.kind)
    if kind is None:
        raise ValueError(f"Item kind {item.kind.value} carries no answer key.")
    gap_ids = _gap_ids_in_body_order(item)
    return AnswerKeyItemView(
        item_id=item.item_id,
        kind=kind,
        title=item.title or "",
        stem_text="\n".join(item.plain_text_lines()),
        choices=tuple((choice_int_id(choice.choice_id), choice.text) for choice in item.choices),
        gap_count=len(gap_ids),
        gap_ids=gap_ids,
        cloze_text=(
            _numbered_cloze_text(item, gap_ids) if kind is AnswerKeyViewKind.GAP_FILL else ""
        ),
    )


def answer_key_item_views(document: NativeExamDocument) -> tuple[AnswerKeyItemView, ...]:
    """Select keyed items whose answer key is absent, in document order."""

    return tuple(
        answer_key_item_view(item)
        for item in document.items
        if item.kind in _VIEW_KIND_BY_ITEM_KIND
        and item.answer_key.origin is NativeAnswerKeyOrigin.ABSENT
    )


def proposal_from_model_content(
    *,
    view: AnswerKeyItemView,
    content: dict[str, JsonValue],
) -> AnswerKeyItemProposal | None:
    """Return a validated proposal from one provider decision, or None."""

    if view.kind is AnswerKeyViewKind.GAP_FILL:
        return _validated_gap_proposal(view=view, content=content)
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


def _int_tuple(value: JsonValue | None) -> tuple[int, ...]:
    if not isinstance(value, list | tuple):
        return ()
    integers: list[int] = []
    for entry in value:
        if not isinstance(entry, int) or isinstance(entry, bool):
            return ()
        integers.append(entry)
    return tuple(integers)


def proposal_from_record(record: WorkspaceAnswerKeyProposalRecord) -> AnswerKeyItemProposal:
    """Rehydrate one persisted proposal record into the typed proposal."""

    return AnswerKeyItemProposal(
        item_id=record.item_id,
        kind=record.kind,
        correct_choice_ids=record.correct_choice_ids,
        gap_accepted_values=tuple(
            (gap_id, values) for gap_id, values in record.gap_accepted_values.items()
        ),
    )


def apply_proposal_to_item(
    item: NativeExamItem,
    proposal: AnswerKeyItemProposal,
) -> NativeExamItem:
    """Return an advisory MACHINE_PROPOSED prefill copy of one item.

    The copy carries the proposed key with ``REVIEW_REQUIRED`` and the
    ``machine_proposed_answer_key`` reason. It is only ever served to the
    editor as prefill material; it must never be written into a saved
    document revision without the teacher's explicit review action.
    """

    if proposal.item_id != item.item_id:
        raise DomainError(
            code=ErrorCode.VALIDATION_ERROR,
            message="Facitförslaget hör till en annan fråga.",
            details={"item_id": item.item_id, "proposal_item_id": proposal.item_id},
        )
    payload = item.model_dump()
    reasons = tuple(payload["review"]["reasons"])
    if MACHINE_PROPOSED_ANSWER_KEY_REVIEW_REASON not in reasons:
        reasons = (*reasons, MACHINE_PROPOSED_ANSWER_KEY_REVIEW_REASON)
    payload["review"] = {
        **payload["review"],
        "state": NativeItemReviewState.REVIEW_REQUIRED,
        "reasons": reasons,
    }
    if proposal.kind is AnswerKeyViewKind.GAP_FILL:
        values_by_gap = dict(proposal.gap_accepted_values)
        if set(values_by_gap) != {gap.gap_id for gap in item.gaps}:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Facitförslaget täcker inte frågans luckor.",
                details={"item_id": item.item_id},
            )
        payload["gaps"] = [
            {**gap_payload, "accepted_values": values_by_gap[gap_payload["gap_id"]]}
            for gap_payload in payload["gaps"]
        ]
        payload["answer_key"] = NativeAnswerKey(
            origin=NativeAnswerKeyOrigin.MACHINE_PROPOSED
        ).model_dump()
    else:
        payload["answer_key"] = NativeAnswerKey(
            origin=NativeAnswerKeyOrigin.MACHINE_PROPOSED,
            correct_choice_ids=proposal.correct_choice_ids,
        ).model_dump()
    return NativeExamItem.model_validate(payload)
