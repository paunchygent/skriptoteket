"""Exam.net PDF item rendering strategies, one per neutral item family.

Purpose:
    Map immutable, source-neutral PDF item semantics into Exam.net PDF item sections,
    warnings, and manual follow-up signals.

Relationships:
    - Implements the `ExamNetPdfItemRenderingStrategy` protocol from
      `examnet_pdf_target_profile` using the helpers in `examnet_pdf_item_rendering`.
    - Selected by the registry in `examnet_pdf_item_registry`.
    - Keeps Exam.net-specific layout labels and target shaping out of parser
      IR, effective IR, bundle, QTI, and service layers.
"""

from __future__ import annotations

from dataclasses import dataclass
from html import escape

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_examnet_pdf_contracts import (
    DigiExamExamNetPdfItemRender,
    DigiExamExamNetPdfWarning,
    DigiExamExamNetPdfWarningCode,
)
from skriptoteket.domain.curated_apps.exam_conversion.exam_pdf_item_semantics import (
    PdfExamItemSemantics,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_pdf_item_rendering import (
    answer_key_mismatch,
    gap_answer_key_html,
    item_shell,
    marking_guide_html,
    match_letter,
    missing_answer_key,
    missing_gap_key_labels,
    option_texts_by_id,
    options_html,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_pdf_target_profile import (
    ExamNetPdfItemStrategyResult,
    ExamNetPdfTargetProfileContext,
)


@dataclass(frozen=True)
class OpenEndedExamNetPdfItemStrategy:
    """Render open-response items as Exam.net PDF free-text sections."""

    def render(
        self,
        *,
        item: PdfExamItemSemantics,
        context: ExamNetPdfTargetProfileContext,
    ) -> ExamNetPdfItemStrategyResult:
        labels = context.label_policy
        return ExamNetPdfItemStrategyResult(
            item=DigiExamExamNetPdfItemRender(
                html=item_shell(
                    item=item,
                    labels=labels,
                    item_type_label=labels.free_text_type_label,
                    instruction="",
                    body_html=marking_guide_html(item, labels),
                    item_type_marker=labels.source_item_type_marker,
                )
            )
        )


@dataclass(frozen=True)
class SingleChoiceExamNetPdfItemStrategy:
    """Render keyed single-answer choice items for the Exam.net PDF target."""

    def render(
        self,
        *,
        item: PdfExamItemSemantics,
        context: ExamNetPdfTargetProfileContext,
    ) -> ExamNetPdfItemStrategyResult:
        option_text_by_id, warnings = option_texts_by_id(item)
        if warnings:
            return ExamNetPdfItemStrategyResult(item=None, warnings=warnings)
        if not option_text_by_id or not item.answer_key.available:
            return ExamNetPdfItemStrategyResult(item=None, warnings=(missing_answer_key(item),))
        if len(item.answer_key.correct_option_ids) != 1:
            return ExamNetPdfItemStrategyResult(
                item=None,
                warnings=(answer_key_mismatch(item, "single-answer choice needs one key"),),
            )

        correct_answer = option_text_by_id.get(item.answer_key.correct_option_ids[0])
        if correct_answer is None:
            return ExamNetPdfItemStrategyResult(
                item=None,
                warnings=(answer_key_mismatch(item, "correct id is not present in options"),),
            )

        labels = context.label_policy
        body_html = options_html(tuple(option_text_by_id.values()))
        body_html += (
            f'<p class="answer-key">{escape(labels.single_answer_key_label)}: '
            f"{escape(correct_answer)}</p>"
        )
        return ExamNetPdfItemStrategyResult(
            item=DigiExamExamNetPdfItemRender(
                html=item_shell(
                    item=item,
                    labels=labels,
                    item_type_label=labels.choice_type_label,
                    instruction="",
                    body_html=body_html,
                    item_type_marker=labels.target_item_type_marker,
                )
            )
        )


@dataclass(frozen=True)
class MultipleResponseExamNetPdfItemStrategy:
    """Render keyed multiple-response items for the Exam.net PDF target."""

    def render(
        self,
        *,
        item: PdfExamItemSemantics,
        context: ExamNetPdfTargetProfileContext,
    ) -> ExamNetPdfItemStrategyResult:
        option_text_by_id, warnings = option_texts_by_id(item)
        if warnings:
            return ExamNetPdfItemStrategyResult(item=None, warnings=warnings)
        if not option_text_by_id or not item.answer_key.available:
            return ExamNetPdfItemStrategyResult(item=None, warnings=(missing_answer_key(item),))
        if not item.answer_key.correct_option_ids:
            return ExamNetPdfItemStrategyResult(
                item=None,
                warnings=(answer_key_mismatch(item, "multiple response needs a key"),),
            )

        correct_answers: list[str] = []
        for correct_id in item.answer_key.correct_option_ids:
            correct_answer = option_text_by_id.get(correct_id)
            if correct_answer is None:
                return ExamNetPdfItemStrategyResult(
                    item=None,
                    warnings=(answer_key_mismatch(item, "correct id is not present in options"),),
                )
            correct_answers.append(correct_answer)

        labels = context.label_policy
        body_html = options_html(tuple(option_text_by_id.values()))
        body_html += (
            f'<p class="answer-key">{escape(labels.multiple_answer_key_label)}: '
            f"{escape('; '.join(correct_answers))}</p>"
        )
        return ExamNetPdfItemStrategyResult(
            item=DigiExamExamNetPdfItemRender(
                html=item_shell(
                    item=item,
                    labels=labels,
                    item_type_label=labels.multiple_response_type_label,
                    instruction="",
                    body_html=body_html,
                    item_type_marker=labels.target_item_type_marker,
                )
            )
        )


@dataclass(frozen=True)
class GapOpenClozeExamNetPdfItemStrategy:
    """Render keyed gap/open-cloze items without relabeling them as free text."""

    def render(
        self,
        *,
        item: PdfExamItemSemantics,
        context: ExamNetPdfTargetProfileContext,
    ) -> ExamNetPdfItemStrategyResult:
        if not item.answer_key.correct_gap_answers:
            return ExamNetPdfItemStrategyResult(item=None, warnings=(missing_answer_key(item),))
        missing_key_labels = missing_gap_key_labels(item, context.label_policy)
        if missing_key_labels:
            return ExamNetPdfItemStrategyResult(
                item=None,
                warnings=(
                    answer_key_mismatch(
                        item,
                        f"missing accepted values for {missing_key_labels}",
                    ),
                ),
            )

        labels = context.label_policy
        body_html = gap_answer_key_html(item, labels)
        return ExamNetPdfItemStrategyResult(
            item=DigiExamExamNetPdfItemRender(
                html=item_shell(
                    item=item,
                    labels=labels,
                    item_type_label=labels.gap_open_cloze_type_label,
                    instruction="",
                    body_html=body_html,
                    item_type_marker=labels.source_item_type_marker,
                )
            )
        )


@dataclass(frozen=True)
class MatchingExamNetPdfItemStrategy:
    """Render keyed matching items: both lists as the student sees them, pairs in the key."""

    def render(
        self,
        *,
        item: PdfExamItemSemantics,
        context: ExamNetPdfTargetProfileContext,
    ) -> ExamNetPdfItemStrategyResult:
        if not item.match_left or not item.answer_key.available:
            return ExamNetPdfItemStrategyResult(item=None, warnings=(missing_answer_key(item),))
        left_text_by_id = {entry.entry_id: entry.text for entry in item.match_left}
        right_text_by_id = {entry.entry_id: entry.text for entry in item.match_right}
        pairs = item.answer_key.correct_match_pairs
        if not pairs:
            return ExamNetPdfItemStrategyResult(item=None, warnings=(missing_answer_key(item),))
        if (
            any(
                pair.left_id not in left_text_by_id or pair.right_id not in right_text_by_id
                for pair in pairs
            )
            or {pair.left_id for pair in pairs} != set(left_text_by_id)
            or len(pairs) != len(left_text_by_id)
        ):
            return ExamNetPdfItemStrategyResult(
                item=None,
                warnings=(answer_key_mismatch(item, "pairs do not key every left entry once"),),
            )

        labels = context.label_policy
        left_html = "".join(
            f"<p>{index}. {escape(entry.text)}</p>"
            for index, entry in enumerate(item.match_left, start=1)
        )
        right_html = "".join(
            f"<p>{match_letter(index)}) {escape(entry.text)}</p>"
            for index, entry in enumerate(item.match_right)
        )
        key_rows = "".join(
            f"<p>{escape(left_text_by_id[pair.left_id])} – "
            f"{escape(right_text_by_id[pair.right_id])}</p>"
            for pair in pairs
        )
        body_html = (
            f'<div class="match-left">{left_html}</div>'
            f'<div class="match-right">{right_html}</div>'
            f'<div class="answer-key"><p>{escape(labels.match_key_label)}:</p>'
            f"{key_rows}</div>"
        )
        return ExamNetPdfItemStrategyResult(
            item=DigiExamExamNetPdfItemRender(
                html=item_shell(
                    item=item,
                    labels=labels,
                    item_type_label=labels.matching_type_label,
                    instruction="",
                    body_html=body_html,
                    item_type_marker=labels.target_item_type_marker,
                )
            )
        )


@dataclass(frozen=True)
class UnsupportedExamNetPdfItemStrategy:
    """Fail closed for neutral item kinds without a governed PDF target shape."""

    def render(
        self,
        *,
        item: PdfExamItemSemantics,
        context: ExamNetPdfTargetProfileContext,
    ) -> ExamNetPdfItemStrategyResult:
        _ = context
        if item.source_item_type_label:
            message = (
                f"Item type {item.source_item_type_label} has no governed Exam.net "
                "PDF-converter target shape yet."
            )
        else:
            message = (
                f"Item kind {item.kind.value} has no governed Exam.net "
                "PDF-converter target shape yet."
            )
        return ExamNetPdfItemStrategyResult(
            item=None,
            warnings=(
                DigiExamExamNetPdfWarning(
                    code=DigiExamExamNetPdfWarningCode.UNSUPPORTED_ITEM_TYPE,
                    message=message,
                    item_id=item.item_id,
                ),
            ),
        )
