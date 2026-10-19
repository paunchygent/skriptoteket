"""Which items block a native exam document's export, and which hold a trusted answer key.

Ordering steps are choices; a blank step blocks as ``empty_ordering_step``.

Export needs every value the export carries, never a parsing doubt (TASK-SKRIPT-39-05-07 D1).
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import is_empty_body
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
    NativeItemReviewState,
    NativeParseOrigin,
)

_TRUSTED_KEY_ORIGINS = frozenset(
    {
        NativeAnswerKeyOrigin.SOURCE_PROVIDED,
        NativeAnswerKeyOrigin.AI_INTERPRETED,
        NativeAnswerKeyOrigin.TEACHER_AUTHORED,
        NativeAnswerKeyOrigin.REVIEWED_ADVISORY,
    }
)

_KEYED_KINDS = frozenset(
    {
        NativeExamItemKind.SINGLE_CHOICE,
        NativeExamItemKind.MULTIPLE_RESPONSE,
        NativeExamItemKind.GAP_FILL,
        NativeExamItemKind.INLINE_CHOICE,
        NativeExamItemKind.MATCHING,
        NativeExamItemKind.ORDERING,
    }
)

_GAP_KINDS = frozenset({NativeExamItemKind.GAP_FILL, NativeExamItemKind.INLINE_CHOICE})


# The fewest options a dropdown gap exports with; one option gives the answer away
# (TASK-SKRIPT-40-04-04 D3). Published to the workspace through the export checklist.
InlineChoiceMinOptions = Literal[2]
INLINE_CHOICE_MIN_OPTIONS: InlineChoiceMinOptions = 2


class NativeExportBlocker(BaseModel):
    """One refusal; `item_id` is None for a refusal that belongs to the exam, not a question."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    item_id: str | None
    reason: Literal[
        "title_without_text",
        "unbuilt_question",
        "machine_proposed_key_unreviewed",
        "missing_points",
        "missing_answer_key",
        "partial_gap_key",
        "gap_without_correct_option",
        "inline_choice_option_heading",
        "empty_choice",
        "empty_gap_option",
        "empty_match_entry",
        "ordering_too_few_steps",
        "empty_ordering_step",
        "too_few_gap_options",
        "empty_question_text",
        "no_gaps",
    ]


def title_has_text(title: str) -> bool:
    """Whether a title has a letter or digit, the least an export file name is built from."""
    return any(char.isalnum() for char in title)


def native_export_blockers(document: NativeExamDocument) -> tuple[NativeExportBlocker, ...]:
    """S4 gate: export needs every value the export carries, never a parsing doubt (D1).

    An unbuilt question, printed from source because the import could not convert it, blocks
    until the teacher marks it reviewed (D2). A named source-picture loss also blocks;
    other converted items that need review do not block.
    Keyed kinds without an answer key block export: Exam.net QTI would carry an
    automatic item with no correct response and the Exam.net PDF prints the key.
    A title without a letter or digit blocks too: every export file is named after the title.
    An ordering question needs two steps and a text in every step; its key is its step order,
    always teacher-authored, so it never lacks one (TASK-SKRIPT-39-06-08).
    A question needs a text, and a gap_fill or inline_choice question needs a gap
    (TASK-SKRIPT-40-04-06 D3, D4); both save while empty.
    A keyed question with an empty Lucktext gap blocks too: a gap with no
    accepted answer is a valid draft the export must refuse (TASK-SKRIPT-40-04-13
    U4, Q9, L2). A keyed dropdown question with a gap that has no correct
    option blocks the same way (`gap_without_correct_option`, the client's
    reason of the same name). One blocker per question per gap kind, even
    when several gaps are empty. A question without an answer key has no empty gaps.
    """
    blockers: list[NativeExportBlocker] = []
    if not title_has_text(document.title):
        blockers.append(NativeExportBlocker(item_id=None, reason="title_without_text"))
    for item in document.items:
        for reason, bodies in (
            (
                (
                    "empty_ordering_step"
                    if item.kind is NativeExamItemKind.ORDERING
                    else "empty_choice"
                ),
                (choice.body for choice in item.choices),
            ),
            ("empty_gap_option", (option.body for gap in item.gaps for option in gap.options)),
            ("empty_match_entry", (entry.body for entry in item.match_left)),
            ("empty_match_entry", (entry.body for entry in item.match_right)),
        ):
            for body in bodies:
                if is_empty_body(body):
                    blockers.append(NativeExportBlocker(item_id=item.item_id, reason=reason))
        if is_empty_body(item.body):
            blockers.append(NativeExportBlocker(item_id=item.item_id, reason="empty_question_text"))
        if item.kind in _GAP_KINDS and not item.gaps:
            blockers.append(NativeExportBlocker(item_id=item.item_id, reason="no_gaps"))
        if item.kind is NativeExamItemKind.ORDERING and len(item.choices) < 2:
            blockers.append(
                NativeExportBlocker(item_id=item.item_id, reason="ordering_too_few_steps")
            )
        if is_unbuilt_question(item):
            blockers.append(NativeExportBlocker(item_id=item.item_id, reason="unbuilt_question"))
        if item.answer_key.origin is NativeAnswerKeyOrigin.MACHINE_PROPOSED:
            blockers.append(
                NativeExportBlocker(
                    item_id=item.item_id,
                    reason="machine_proposed_key_unreviewed",
                )
            )
        if item.kind in _KEYED_KINDS and item.answer_key.origin is NativeAnswerKeyOrigin.ABSENT:
            blockers.append(NativeExportBlocker(item_id=item.item_id, reason="missing_answer_key"))
        if _has_empty_gap_fill(item):
            blockers.append(NativeExportBlocker(item_id=item.item_id, reason="partial_gap_key"))
        if _has_empty_dropdown_gap(item):
            blockers.append(
                NativeExportBlocker(item_id=item.item_id, reason="gap_without_correct_option")
            )
        if item.kind is NativeExamItemKind.INLINE_CHOICE and any(
            paragraph.heading_level is not None
            for gap in item.gaps
            for option in gap.options
            for paragraph in option.body
        ):
            blockers.append(
                NativeExportBlocker(item_id=item.item_id, reason="inline_choice_option_heading")
            )
        if item.kind is NativeExamItemKind.INLINE_CHOICE and any(
            len(gap.options) < INLINE_CHOICE_MIN_OPTIONS for gap in item.gaps
        ):
            blockers.append(NativeExportBlocker(item_id=item.item_id, reason="too_few_gap_options"))
        if item.points is None:
            blockers.append(NativeExportBlocker(item_id=item.item_id, reason="missing_points"))
    return tuple(blockers)


def _has_keyed_origin(item: NativeExamItem) -> bool:
    """Whether the question carries an answer key; a question without one has no empty gaps (Q9)."""
    return item.answer_key.origin not in (
        NativeAnswerKeyOrigin.ABSENT,
        NativeAnswerKeyOrigin.NOT_APPLICABLE,
    )


def _has_empty_gap_fill(item: NativeExamItem) -> bool:
    """A keyed Lucktext question with a gap that holds no accepted answer (Q9)."""
    return (
        item.kind is NativeExamItemKind.GAP_FILL
        and _has_keyed_origin(item)
        and any(not gap.accepted_values for gap in item.gaps)
    )


def _has_empty_dropdown_gap(item: NativeExamItem) -> bool:
    """A keyed dropdown question with a gap that names no correct option (Q9)."""
    return (
        item.kind is NativeExamItemKind.INLINE_CHOICE
        and _has_keyed_origin(item)
        and any(gap.correct_option_id is None for gap in item.gaps)
    )


def is_unbuilt_question(item: NativeExamItem) -> bool:
    """An unfinished source question, including a named picture loss, pending teacher review."""
    missing_picture = item.retry_source is not None and item.retry_source.has_missing_pictures()
    return item.review.state is NativeItemReviewState.REVIEW_REQUIRED and (
        item.review.parse_origin is NativeParseOrigin.SOURCE_FALLBACK or missing_picture
    )


def item_has_trusted_key(item: NativeExamItem) -> bool:
    if item.kind not in _KEYED_KINDS:
        return False
    return item.answer_key.origin in _TRUSTED_KEY_ORIGINS
