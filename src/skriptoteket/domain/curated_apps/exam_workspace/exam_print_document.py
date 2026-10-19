"""The one format-neutral print document for printed exams (TASK-SKRIPT-40-04-07 W1-W9).

Purpose:
    Turn a native exam document into the single content model every print surface
    renders. The student PDF, the facit PDF and the DOCX student copy read this
    ``PrintDocument`` and nothing else, so all three print the same blocks in the
    same order. ``build_print_document`` fixes that order once per variant.

    ``ExamPrintVariant.STUDENT`` holds writing areas and answer forms and no
    answers (W1, W6, W7, W8, W9). ``ExamPrintVariant.FACIT`` holds the same blocks,
    plus after each question that has one its answer key and criteria (W1).

    The document is format-neutral: it names text, handwriting blanks, pictures,
    ruled writing lines, ticked options, a matching grid and an answer key, and it
    never names a font, a page or a file format. The DOCX renderer and the
    print-PDF HTML renderer (other units) render only this.

Relationships:
    Reads the item print layout (``exam_print_layout``), the house template's blank
    minimum (``exam_conversion.exam_print_house_template``), the Swedish export
    labels (``exam_language_labels``) and the generated header
    (``exam_export_header``). It copies the DOCX writer's content order and its
    facit wording; it is a pure leaf builder and writes nothing back. It numbers
    every question with the workspace list label (``native_exam_list_labels``),
    the same label the question list and the editor heading show.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum

from skriptoteket.domain.curated_apps.exam_conversion.exam_print_house_template import (
    BLANK_MIN_WIDTH_MM,
    ExamPrintVariant,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_export_header import (
    exam_export_header_lines,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_language_labels import (
    SWEDISH_EXAM_LABELS,
    ExamExportLabels,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_print_layout import (
    ItemPrintLayout,
    ParagraphPrintRole,
    item_print_layout,
    paragraph_print_role,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeAssetSegment,
    NativeGapSegment,
    NativeParagraph,
    NativeTextSegment,
    is_empty_body,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_list_labels import (
    native_exam_question_labels,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_outline import (
    OutlineQuestion,
    document_outline,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeChoice,
    NativeGap,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_plain_text

_CHOICE_KINDS = (
    NativeExamItemKind.SINGLE_CHOICE,
    NativeExamItemKind.MULTIPLE_RESPONSE,
)


@dataclass(frozen=True)
class PrintText:
    """A run of printed text."""

    text: str


@dataclass(frozen=True)
class PrintBlank:
    """A writable handwriting blank inside a sentence, sized for its accepted answer (W7)."""

    width_mm: float


@dataclass(frozen=True)
class PrintImage:
    """A picture placed at its exact source position."""

    asset_id: str


PrintRun = PrintText | PrintBlank | PrintImage


class PrintParagraphStyle(StrEnum):
    """How one printed paragraph is spaced and treated."""

    BODY = "body"
    GAP_LINE = "gap_line"  # writing-height spacing so a sentence's blanks stay writable (W7)
    POINTS = "points"
    DETAIL = "detail"  # a generated header line, such as the course or the total


class PrintBox(StrEnum):
    """The box a printed answer form carries (W8)."""

    TICK = "tick"
    NUMBER = "number"


@dataclass(frozen=True)
class PrintHeading:
    """A printed heading; level 1 is the exam title, level 3 a question title."""

    level: int
    text: str


@dataclass(frozen=True)
class PrintParagraph:
    """One paragraph of positioned runs."""

    runs: tuple[PrintRun, ...]
    style: PrintParagraphStyle


@dataclass(frozen=True)
class PrintRuledLines:
    """A ruled writing area (W9); one full-width answer line is ``count`` 1."""

    count: int


@dataclass(frozen=True)
class PrintOption:
    """One answer form: ``label`` "A)" for a choice, empty for an ordering step."""

    box: PrintBox
    label: str
    text: str


@dataclass(frozen=True)
class PrintGrid:
    """A matching item's two lists; the renderer prints one tick box per cell (W8)."""

    rows: tuple[str, ...]
    columns: tuple[str, ...]


@dataclass(frozen=True)
class PrintAnswerKey:
    """A facit answer key or marking guide; it never appears in the student copy (W1)."""

    lines: tuple[str, ...]


PrintBlock = (
    PrintHeading | PrintParagraph | PrintRuledLines | PrintOption | PrintGrid | PrintAnswerKey
)


@dataclass(frozen=True)
class PrintInstruction:
    """A shared instruction block: the exam header or one parent's wording."""

    blocks: tuple[PrintBlock, ...]


@dataclass(frozen=True)
class PrintQuestion:
    """One question's printed blocks in two explicit groups (TASK-SKRIPT-40-04-12 K8).

    ``text`` is the question text: the heading, every body block including gap
    lines and one-line answer lines from ANSWER_LINE paragraphs, and the points
    paragraph. ``answer`` is the answer form: the FREE_TEXT writing area, the
    choice or ordering options, the matching grid, and the facit answer key.
    The two groups concatenate to the DOCX writer's today order, text first.
    """

    item_id: str
    text: tuple[PrintBlock, ...]
    answer: tuple[PrintBlock, ...]


@dataclass(frozen=True)
class PrintDocument:
    """The complete print content of one exam for one variant."""

    variant: ExamPrintVariant
    title: str
    entries: tuple[PrintInstruction | PrintQuestion, ...]


def build_print_document(
    document: NativeExamDocument, *, variant: ExamPrintVariant
) -> PrintDocument:
    """Build the format-neutral print document of ``document`` for ``variant``."""
    title, *details = exam_export_header_lines(document)
    header_blocks: list[PrintBlock] = [PrintHeading(level=1, text=title)]
    header_blocks.extend(
        PrintParagraph(runs=(PrintText(text),), style=PrintParagraphStyle.DETAIL)
        for text in details
    )
    header_blocks.extend(_instruction_blocks(document.printed_instructions()))
    question_labels = native_exam_question_labels(document)
    entries: tuple[PrintInstruction | PrintQuestion, ...] = (
        PrintInstruction(blocks=tuple(header_blocks)),
        *_print_walk(document, variant=variant, question_labels=question_labels),
    )
    return PrintDocument(variant=variant, title=title, entries=entries)


def _print_walk(
    document: NativeExamDocument,
    *,
    variant: ExamPrintVariant,
    question_labels: Mapping[str, str],
) -> tuple[PrintInstruction | PrintQuestion, ...]:
    """Every entry after the exam header, in the one outline order.

    The walk reads the native exam outline owner: a standalone question prints
    its own question, and a part prints its instruction (unless empty) followed
    by one question per child, in order. A childless part with a non-empty
    instruction prints only its instruction at its own place; a childless part
    with an empty instruction prints nothing. Every question heading uses its
    workspace list label from ``question_labels``, computed once per document.
    """
    entries: list[PrintInstruction | PrintQuestion] = []
    for entry in document_outline(document):
        if isinstance(entry, OutlineQuestion):
            groups = _question_blocks(
                entry.item,
                variant=variant,
                question_label=question_labels[entry.item.item_id],
            )
            entries.append(
                PrintQuestion(
                    item_id=entry.item.item_id,
                    text=groups.text,
                    answer=groups.answer,
                )
            )
            continue
        if not is_empty_body(entry.part.instruction):
            entries.append(PrintInstruction(blocks=_instruction_blocks(entry.part.instruction)))
        for child in entry.children:
            groups = _question_blocks(
                child, variant=variant, question_label=question_labels[child.item_id]
            )
            entries.append(
                PrintQuestion(item_id=child.item_id, text=groups.text, answer=groups.answer)
            )
    return tuple(entries)


def _instruction_blocks(body: Iterable[NativeParagraph]) -> tuple[PrintBlock, ...]:
    """Shared instruction body paragraphs as plain printed paragraphs.

    Every text segment keeps its place, every picture prints at its exact source
    position and a response gap (which a shared instruction never carries) would
    print its minimum blank.
    """
    return tuple(
        PrintParagraph(runs=_instruction_runs(paragraph), style=PrintParagraphStyle.BODY)
        for paragraph in body
    )


def _instruction_runs(paragraph: NativeParagraph) -> tuple[PrintRun, ...]:
    runs: list[PrintRun] = []
    for segment in paragraph.segments:
        if isinstance(segment, NativeTextSegment):
            runs.append(PrintText(segment.text))
        elif isinstance(segment, NativeAssetSegment):
            runs.append(PrintImage(asset_id=segment.asset_id))
        else:
            runs.append(PrintBlank(width_mm=BLANK_MIN_WIDTH_MM))
    return tuple(runs)


@dataclass(frozen=True)
class QuestionBlockGroups:
    """One question's blocks split into the text group and the answer-form group."""

    text: tuple[PrintBlock, ...]
    answer: tuple[PrintBlock, ...]


def _question_blocks(
    item: NativeExamItem, *, variant: ExamPrintVariant, question_label: str
) -> QuestionBlockGroups:
    """One question's blocks, in the DOCX writer's today order (W1, W6-W9).

    The heading names the question with its workspace list label ("2", "1b"),
    never its running sequence.
    """
    labels = SWEDISH_EXAM_LABELS
    layout = item_print_layout(item)
    gaps_by_id = {gap.gap_id: gap for gap in item.gaps}
    text: list[PrintBlock] = [PrintHeading(level=3, text=labels.question_label(question_label))]
    answer: list[PrintBlock] = []

    for paragraph in item.body:
        role = paragraph_print_role(item, paragraph)
        if role is ParagraphPrintRole.ANSWER_LINE:
            text.append(PrintRuledLines(count=1))
        elif role is ParagraphPrintRole.GAP_LINE:
            text.append(
                PrintParagraph(
                    runs=_gap_line_runs(paragraph, layout),
                    style=PrintParagraphStyle.GAP_LINE,
                )
            )
        else:
            runs = _text_paragraph_runs(paragraph, gaps_by_id)
            if runs:
                text.append(PrintParagraph(runs=runs, style=PrintParagraphStyle.BODY))

    text.append(
        PrintParagraph(
            runs=(PrintText(_points_line(item, labels)),),
            style=PrintParagraphStyle.POINTS,
        )
    )

    if item.kind is NativeExamItemKind.FREE_TEXT:
        answer.append(PrintRuledLines(count=layout.writing_lines))
    elif item.kind in _CHOICE_KINDS:
        for index, choice in enumerate(item.choices):
            answer.append(
                PrintOption(
                    box=PrintBox.TICK,
                    label=f"{_choice_letter(index)})",
                    text=body_plain_text(choice.body),
                )
            )
    elif item.kind is NativeExamItemKind.ORDERING:
        for choice in _ordering_steps_in_print_order(item):
            answer.append(
                PrintOption(box=PrintBox.NUMBER, label="", text=body_plain_text(choice.body))
            )
    elif item.kind is NativeExamItemKind.MATCHING:
        answer.append(
            PrintGrid(
                rows=tuple(body_plain_text(entry.body) for entry in item.match_left),
                columns=tuple(body_plain_text(entry.body) for entry in item.match_right),
            )
        )

    if variant is ExamPrintVariant.FACIT:
        key_lines = _facit_lines(item, labels)
        if key_lines:
            answer.append(PrintAnswerKey(lines=key_lines))
    return QuestionBlockGroups(text=tuple(text), answer=tuple(answer))


def _text_paragraph_runs(
    paragraph: NativeParagraph, gaps_by_id: Mapping[str, NativeGap]
) -> tuple[PrintRun, ...]:
    """A body paragraph as printed runs; an inline choice gap prints its option list.

    An ``inline_choice`` gap has no writable blank: it prints its options between
    brackets, exactly as the DOCX writer's ``_item_text_lines`` does (W8).
    """
    runs: list[PrintRun] = []
    for segment in paragraph.segments:
        if isinstance(segment, NativeTextSegment):
            runs.append(PrintText(segment.text))
        elif isinstance(segment, NativeAssetSegment):
            runs.append(PrintImage(asset_id=segment.asset_id))
        elif isinstance(segment, NativeGapSegment):
            gap = gaps_by_id[segment.gap_id]
            options = " / ".join(body_plain_text(option.body) for option in gap.options)
            runs.append(PrintText(f"[{options}]"))
    return tuple(runs)


def _gap_line_runs(paragraph: NativeParagraph, layout: ItemPrintLayout) -> tuple[PrintRun, ...]:
    """A gap-line paragraph: its wording, pictures and one sized blank per gap (W7)."""
    runs: list[PrintRun] = []
    for segment in paragraph.segments:
        if isinstance(segment, NativeTextSegment):
            runs.append(PrintText(segment.text))
        elif isinstance(segment, NativeAssetSegment):
            runs.append(PrintImage(asset_id=segment.asset_id))
        elif isinstance(segment, NativeGapSegment):
            runs.append(PrintBlank(width_mm=layout.gap_forms[segment.gap_id].width_mm))
    return tuple(runs)


def _points_line(item: NativeExamItem, labels: ExamExportLabels) -> str:
    return labels.points_line(None if item.points is None else _format_points(item.points))


def _format_points(points: int | float) -> str:
    if isinstance(points, int) or float(points).is_integer():
        return str(int(points))
    return str(points).replace(".", ",")


def _choice_letter(index: int) -> str:
    if index < 26:
        return chr(ord("A") + index)
    return str(index + 1)


def _ordering_steps_in_print_order(item: NativeExamItem) -> tuple[NativeChoice, ...]:
    choice_by_id = {choice.choice_id: choice for choice in item.choices}
    return tuple(choice_by_id[choice_id] for choice_id in item.print_order)


def _facit_lines(item: NativeExamItem, labels: ExamExportLabels) -> tuple[str, ...]:
    """One item's answer key and criteria: the facit wording the DOCX writer moved here."""
    if item.kind is NativeExamItemKind.FREE_TEXT:
        if not item.criteria:
            return ()
        return (
            f"{labels.marking_guide}:",
            *(f"• {criterion.text} ({criterion.points} p)" for criterion in item.criteria),
        )
    if item.kind in _CHOICE_KINDS and item.answer_key.correct_choice_ids:
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
            for choice in _ordering_steps_in_print_order(item)
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
