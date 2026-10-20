"""The answer-side print content for printed exams: options, ordering and facit.

Purpose:
    Own the answer forms' derived content so the format-neutral print document
    stays a thin assembler. ``choice_letter`` names choice labels,
    ``ordering_steps_in_print_order`` returns ordering steps in their print
    order and ``facit_lines`` builds one item's answer key and criteria lines.

Relationships:
    Reads the native exam item and vocabulary (``native_exam_item``,
    ``native_exam_vocabulary``, ``native_exam_values``), the Swedish export
    labels (``exam_language_labels``) and the shared body text
    (``shared_body``). It writes nothing back. ``exam_print_document`` imports
    these three names and renders only their results.
"""

from skriptoteket.domain.curated_apps.exam_workspace.exam_language_labels import (
    ExamExportLabels,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeChoice,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_plain_text

CHOICE_KINDS = (  # the item kinds that print tick-box options.
    NativeExamItemKind.SINGLE_CHOICE,
    NativeExamItemKind.MULTIPLE_RESPONSE,
)


def choice_letter(index: int) -> str:
    if index < 26:
        return chr(ord("A") + index)
    return str(index + 1)


def ordering_steps_in_print_order(item: NativeExamItem) -> tuple[NativeChoice, ...]:
    choice_by_id = {choice.choice_id: choice for choice in item.choices}
    return tuple(choice_by_id[choice_id] for choice_id in item.print_order)


def facit_lines(item: NativeExamItem, labels: ExamExportLabels) -> tuple[str, ...]:
    """One item's answer key and criteria: the facit wording the DOCX writer moved here."""
    if item.kind is NativeExamItemKind.FREE_TEXT:
        if not item.criteria:
            return ()
        return (
            f"{labels.marking_guide}:",
            *(
                f"• {criterion.text} {labels.points_inline(str(criterion.points))}"
                for criterion in item.criteria
            ),
        )
    if item.kind in CHOICE_KINDS and item.answer_key.correct_choice_ids:
        text_by_choice_id = {
            choice.choice_id: body_plain_text(choice.body) for choice in item.choices
        }
        correct_texts = tuple(
            text_by_choice_id[choice_id] for choice_id in item.answer_key.correct_choice_ids
        )
        return (labels.keyed(labels.correct_answer, "; ".join(correct_texts)),)
    if item.kind is NativeExamItemKind.GAP_FILL and any(gap.accepted_values for gap in item.gaps):
        return tuple(
            labels.keyed(labels.gap_label(index), " / ".join(gap.accepted_values))
            for index, gap in enumerate(item.gaps, start=1)
        )
    if item.kind is NativeExamItemKind.INLINE_CHOICE:
        return tuple(
            labels.keyed(
                labels.gap_label(index),
                body_plain_text(
                    next(
                        option.body
                        for option in gap.options
                        if option.choice_id == gap.correct_option_id
                    )
                ),
            )
            for index, gap in enumerate(item.body_gaps(), start=1)
        )
    if item.kind is NativeExamItemKind.ORDERING:
        number_by_id = {
            choice.choice_id: index for index, choice in enumerate(item.choices, start=1)
        }
        steps = "; ".join(
            f"{body_plain_text(choice.body)} {number_by_id[choice.choice_id]}"
            for choice in ordering_steps_in_print_order(item)
        )
        return (labels.keyed(labels.correct_order, steps),)
    if item.kind is NativeExamItemKind.MATCHING and item.answer_key.match_pairs:
        left = {entry.left_id: body_plain_text(entry.body) for entry in item.match_left}
        right = {entry.right_id: body_plain_text(entry.body) for entry in item.match_right}
        return tuple(
            labels.keyed(labels.pair, f"{left[pair.left_id]} – {right[pair.right_id]}")
            for pair in item.answer_key.match_pairs
        )
    return ()
