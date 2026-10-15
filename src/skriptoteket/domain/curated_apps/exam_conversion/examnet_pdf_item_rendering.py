"""Exam.net PDF item rendering helpers shared by the item strategies.

Purpose:
    Build the item section shell, option, gap, criteria and match HTML, and the
    answer-key warnings, that every Exam.net PDF item strategy composes.

Relationships:
    - Reads `domain.exam_pdf_item_semantics` values and the label policy from
      `examnet_pdf_target_profile`.
    - Called by the strategies in `examnet_pdf_item_strategies`.
"""

from __future__ import annotations

import re
from html import escape

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_examnet_pdf_contracts import (
    DigiExamExamNetPdfWarning,
    DigiExamExamNetPdfWarningCode,
)
from skriptoteket.domain.curated_apps.exam_conversion.exam_pdf_item_semantics import (
    PdfExamItemSemantics,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_pdf_target_profile import (
    ExamNetPdfItemLabelPolicy,
)

_LABELLED_OPTION_PATTERN = re.compile(r"^(?:[A-Za-z]|\d+)[.)]\s+")


def option_texts_by_id(
    item: PdfExamItemSemantics,
) -> tuple[dict[int, str], tuple[DigiExamExamNetPdfWarning, ...]]:
    option_text_by_id: dict[int, str] = {}
    warnings: list[DigiExamExamNetPdfWarning] = []
    for option in item.options:
        option_text = _target_option_text(option.text)
        if option_text == "":
            continue
        option_text_by_id[option.option_id] = option_text

    if len(set(option_text_by_id.values())) != len(option_text_by_id):
        return {}, (answer_key_mismatch(item, "duplicate option text is unsafe"),)
    return option_text_by_id, tuple(warnings)


def _target_option_text(source_text: str) -> str:
    normalized_text = " ".join(source_text.split())
    return _LABELLED_OPTION_PATTERN.sub("", normalized_text, count=1)


def missing_answer_key(item: PdfExamItemSemantics) -> DigiExamExamNetPdfWarning:
    return DigiExamExamNetPdfWarning(
        code=DigiExamExamNetPdfWarningCode.MANUAL_ANSWER_KEY_REQUIRED,
        message=f"Item {item.item_id} needs source-proven answer-key data before PDF render.",
        item_id=item.item_id,
    )


def answer_key_mismatch(
    item: PdfExamItemSemantics,
    reason: str,
) -> DigiExamExamNetPdfWarning:
    return DigiExamExamNetPdfWarning(
        code=DigiExamExamNetPdfWarningCode.ALTERNATIVE_ANSWER_KEY_MISMATCH,
        message=f"Item {item.item_id} cannot render safely: {reason}.",
        item_id=item.item_id,
    )


def match_letter(index: int) -> str:
    if index < 26:
        return chr(ord("A") + index)
    return str(index + 1)


def options_html(options: tuple[str, ...]) -> str:
    options_html = "".join(f"<p>{escape(option)}</p>" for option in options)
    return f'<div class="options">{options_html}</div>'


def missing_gap_key_labels(
    item: PdfExamItemSemantics,
    labels: ExamNetPdfItemLabelPolicy,
) -> str:
    values_by_gap_id = _gap_values_by_gap_id(item)
    missing_labels = tuple(
        f"{labels.gap_label} {index}"
        for index, gap in enumerate(item.gaps, start=1)
        if not values_by_gap_id.get(gap.gap_id)
    )
    return ", ".join(missing_labels)


def gap_answer_key_html(
    item: PdfExamItemSemantics,
    labels: ExamNetPdfItemLabelPolicy,
) -> str:
    values_by_gap_id = _gap_values_by_gap_id(item)
    if len(item.gaps) == 1:
        values = values_by_gap_id.get(item.gaps[0].gap_id, ())
        return (
            f'<p class="answer-key">{escape(labels.multiple_answer_key_label)}: '
            f"{escape('; '.join(values))}</p>"
        )
    rows = "".join(
        f"<p>{escape(labels.gap_label)} {index}: "
        f"{escape('; '.join(values_by_gap_id.get(gap.gap_id, ())))}</p>"
        for index, gap in enumerate(item.gaps, start=1)
    )
    return f'<div class="answer-key"><p>{escape(labels.multiple_answer_key_label)}:</p>{rows}</div>'


def criteria_html(item: PdfExamItemSemantics, labels: ExamNetPdfItemLabelPolicy) -> str:
    if not item.criteria:
        return ""
    rows = "".join(
        f"<li>{escape(criterion.text).replace(chr(10), '<br>')} ({criterion.points} p)</li>"
        for criterion in item.criteria
    )
    return (
        f'<div class="answer-key"><p>{escape(labels.marking_guide_label)}:</p><ul>{rows}</ul></div>'
    )


def _gap_values_by_gap_id(item: PdfExamItemSemantics) -> dict[str, tuple[str, ...]]:
    values_by_gap_id: dict[str, list[str]] = {gap.gap_id: [] for gap in item.gaps}
    for answer in item.answer_key.correct_gap_answers:
        value = answer.value.strip()
        if value and answer.gap_id in values_by_gap_id:
            values_by_gap_id[answer.gap_id].append(value)
    return {gap_id: tuple(values) for gap_id, values in values_by_gap_id.items()}


def item_shell(
    *,
    item: PdfExamItemSemantics,
    labels: ExamNetPdfItemLabelPolicy,
    item_type_label: str,
    instruction: str,
    body_html: str,
    item_type_marker: str,
) -> str:
    instruction_html = f"<p>{escape(instruction)}</p>" if instruction else ""
    return (
        '<section class="exam-item">'
        f"<h2>Fråga {item.sequence}</h2>"
        f'<p class="points">{escape(labels.point_label)}: {item.points}</p>'
        f'<p class="item-type">{escape(item_type_marker)}: {escape(item_type_label)}</p>'
        f"{instruction_html}"
        f'<div class="prompt">{item.prompt_html}</div>'
        f"{body_html}"
        "</section>"
    )
