"""Shared items and inspectors for the print-document suites, student and facit."""

from skriptoteket.domain.curated_apps.exam_workspace.exam_print_document import (
    PrintAnswerKey,
    PrintBlank,
    PrintBlock,
    PrintDocument,
    PrintGrid,
    PrintHeading,
    PrintOption,
    PrintParagraph,
    PrintQuestion,
    PrintText,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeGapSegment,
    NativeParagraph,
    NativeSegment,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_criteria import (
    NativeExamCriterion,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKey,
    NativeChoice,
    NativeGap,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_free_text_item,
    make_review,
    plain_body,
)


def segments_paragraph(*segments: NativeSegment) -> NativeParagraph:
    return NativeParagraph(heading_level=None, segments=segments)


def free_text_item(
    *,
    sequence: int = 1,
    item_id: str = "item_001",
    writing_lines: int = 5,
    criteria: tuple[NativeExamCriterion, ...] = (),
) -> NativeExamItem:
    points = sum(criterion.points for criterion in criteria) if criteria else 4
    payload = make_free_text_item(sequence=sequence, item_id=item_id).model_dump()
    payload.update(
        writing_lines=writing_lines,
        points=points,
        criteria=[criterion.model_dump() for criterion in criteria],
    )
    return NativeExamItem.model_validate(payload)


def gap_fill_item(
    body: tuple[NativeParagraph, ...],
    gaps: tuple[NativeGap, ...],
    *,
    sequence: int = 1,
    item_id: str = "item_001",
    origin: NativeAnswerKeyOrigin = NativeAnswerKeyOrigin.SOURCE_PROVIDED,
) -> NativeExamItem:
    return NativeExamItem(
        item_id=item_id,
        sequence=sequence,
        kind=NativeExamItemKind.GAP_FILL,
        body=body,
        points=2,
        gaps=gaps,
        answer_key=NativeAnswerKey(origin=origin),
        review=make_review(),
    )


def lone_gap_item(
    *, sequence: int = 1, item_id: str = "item_001", accepted: tuple[str, ...] = ("NF",)
) -> NativeExamItem:
    return gap_fill_item(
        (segments_paragraph(NativeGapSegment(gap_id="gap_001")),),
        (NativeGap(gap_id="gap_001", accepted_values=accepted),),
        sequence=sequence,
        item_id=item_id,
    )


def inline_choice_item() -> NativeExamItem:
    return NativeExamItem(
        item_id="item_001",
        sequence=1,
        kind=NativeExamItemKind.INLINE_CHOICE,
        body=(
            segments_paragraph(
                NativeTextSegment(text="Vattnets formel är ", marks=()),
                NativeGapSegment(gap_id="gap_001"),
            ),
        ),
        points=2,
        gaps=(
            NativeGap(
                gap_id="gap_001",
                options=(
                    NativeChoice(choice_id="choice_001", body=plain_body("H2O")),
                    NativeChoice(choice_id="choice_002", body=plain_body("CO2")),
                ),
                correct_option_id="choice_001",
            ),
        ),
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED),
        review=make_review(),
    )


def question(document: PrintDocument, item_id: str) -> PrintQuestion:
    return next(
        entry
        for entry in document.entries
        if isinstance(entry, PrintQuestion) and entry.item_id == item_id
    )


def all_blocks(document: PrintDocument) -> tuple[PrintBlock, ...]:
    return tuple(block for entry in document.entries for block in entry.blocks)


def all_texts(document: PrintDocument) -> tuple[str, ...]:
    texts: list[str] = []
    for block in all_blocks(document):
        if isinstance(block, (PrintHeading, PrintOption)):
            texts.append(block.text)
        elif isinstance(block, PrintParagraph):
            texts.extend(run.text for run in block.runs if isinstance(run, PrintText))
        elif isinstance(block, PrintGrid):
            texts.extend(block.rows)
            texts.extend(block.columns)
        elif isinstance(block, PrintAnswerKey):
            texts.extend(block.lines)
    return tuple(texts)


def has_blank(document: PrintDocument) -> bool:
    return any(
        any(isinstance(run, PrintBlank) for run in block.runs)
        for block in all_blocks(document)
        if isinstance(block, PrintParagraph)
    )


def has_answer_key(document: PrintDocument) -> bool:
    return any(isinstance(block, PrintAnswerKey) for block in all_blocks(document))
