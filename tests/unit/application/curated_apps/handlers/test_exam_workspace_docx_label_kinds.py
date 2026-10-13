"""Ordering enumeration is gone from the final presentation; part labels stay (D36).

Replays the live recordings of every corpus exam through the production pipeline, then reads
the saved document, the DOCX export and the QTI export. A number or letter that orders the
questions or a question's choices does not reach any of them; an "a)" or "b)" that names a
part inside one question's body reaches all of them as the source prints it.
"""

import io
import re
from collections.abc import Iterator
from xml.etree import ElementTree

import pytest
from docx import Document

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import ExamNetQtiItem
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_item_xml import (
    serialize_qti_assessment_item,
)
from skriptoteket.domain.curated_apps.exam_workspace.examnet_qti_export import (
    native_exam_to_examnet_qti_items,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeExamItem,
    NativeExamItemKind,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_writer import (  # noqa: E501
    ExamWorkspaceDocxWriter,
)
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
    build_replay,
    corpus_chunks,
    recorded_exams,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

_PART_LABEL = re.compile(r"^[a-z]\)\s\S")
_QUESTION_NUMBER = re.compile(r"^\s*\d{1,3}[.)]\s")
_CHOICE_ENUMERATION = re.compile(r"^\s*\(?(?:[A-Za-z]|\d{1,3})[.)]\s")
_CHOICE_KINDS = (NativeExamItemKind.SINGLE_CHOICE, NativeExamItemKind.MULTIPLE_RESPONSE)
_converted: dict[str, NativeExamDocument] = {}


async def _document(exam: str) -> NativeExamDocument:
    if exam not in _converted:
        replay = build_replay(exam)
        _converted[exam] = (await replay.pipeline.convert(job=replay.job())).update.document
    return _converted[exam]


def _squash(text: str) -> str:
    return " ".join(text.split())


def _qti_items(document: NativeExamDocument) -> dict[str, ExamNetQtiItem]:
    """Every exported QTI item by native item id; a parent's children are exported inside it."""

    def walk(items: tuple[ExamNetQtiItem, ...]) -> Iterator[ExamNetQtiItem]:
        for item in items:
            yield item
            yield from walk(item.children)

    return {item.item_id: item for item in walk(native_exam_to_examnet_qti_items(document))}


def _qti_text(item: ExamNetQtiItem) -> str:
    root = ElementTree.fromstring(serialize_qti_assessment_item(item))
    return _squash(" ".join(root.itertext()))


def _docx_paragraphs(document: NativeExamDocument) -> list[str]:
    content = ExamWorkspaceDocxWriter().build_docx_bytes(document)
    return [paragraph.text for paragraph in Document(io.BytesIO(content)).paragraphs]


def _part_label_items(document: NativeExamDocument) -> list[NativeExamItem]:
    return [
        item
        for item in document.items
        if any(_PART_LABEL.match(line) for line in item.plain_text_lines())
    ]


def _source_text(exam: str) -> str:
    return _squash(" ".join(chunk.text for chunk in corpus_chunks(exam)))


def _leading(line: str) -> str:
    """The part label and the first words after it, enough to find the line anywhere."""
    return _squash(line)[:14]


@pytest.mark.parametrize("exam", recorded_exams())
async def test_part_labels_inside_a_body_reach_the_document_and_both_exports_as_printed(exam: str):
    document = await _document(exam)
    items = _part_label_items(document)
    if not items:
        pytest.skip("this exam prints no part labels inside a question body")
    paragraphs = _docx_paragraphs(document)
    qti = _qti_items(document)

    for item in items:
        part_lines = [line for line in item.plain_text_lines() if _PART_LABEL.match(line)]
        source = _source_text(exam)
        assert part_lines
        for line in part_lines:
            assert _leading(line) in source, f"{item.item_id}: label moved or reworded"
            assert line in paragraphs, f"{item.item_id}: DOCX export lost {line[:20]!r}"
            assert _leading(line) in _qti_text(qti[item.item_id]), (
                f"{item.item_id}: QTI export lost {line[:20]!r}"
            )
        assert item.printed_label not in {line[0] for line in part_lines}


async def test_the_recorded_corpus_holds_a_free_text_item_with_several_part_labels():
    kept = [
        item
        for exam in recorded_exams()
        for item in _part_label_items(await _document(exam))
        if item.kind is NativeExamItemKind.FREE_TEXT
        and sum(bool(_PART_LABEL.match(line)) for line in item.plain_text_lines()) >= 2
    ]

    assert kept, "no recorded free-text item keeps its a) and b) lines as separate parts"


@pytest.mark.parametrize("exam", recorded_exams())
async def test_choices_carry_no_ordering_letter_in_the_document_or_the_qti_export(exam: str):
    document = await _document(exam)
    qti = _qti_items(document)

    for item in document.items:
        if item.kind not in _CHOICE_KINDS:
            continue
        exported = [choice.text for choice in qti[item.item_id].choices]
        assert exported == [_squash(choice.text) for choice in item.choices]
        for choice in item.choices:
            assert not _CHOICE_ENUMERATION.match(choice.text), (item.item_id, choice.text[:30])


@pytest.mark.parametrize("exam", recorded_exams())
async def test_the_docx_export_adds_one_letter_per_choice_and_never_doubles_it(exam: str):
    document = await _document(exam)
    paragraphs = _docx_paragraphs(document)

    for item in document.items:
        if item.kind not in _CHOICE_KINDS:
            continue
        for index, choice in enumerate(item.choices):
            letter = chr(ord("A") + index)
            assert f"{letter}) {choice.text}" in paragraphs


@pytest.mark.parametrize("exam", recorded_exams())
async def test_a_stem_whose_source_starts_with_its_number_exports_without_it(exam: str):
    document = await _document(exam)
    paragraphs = _docx_paragraphs(document)
    qti = _qti_items(document)
    numbered = [
        item
        for item in document.items
        if _QUESTION_NUMBER.match(
            " ".join(c.text for c in corpus_chunks(exam) if c.anchor == item.source_anchor)
        )
    ]
    if not numbered:
        pytest.skip("no source question of this exam starts with its number")

    for item in numbered:
        assert not _QUESTION_NUMBER.match(item.plain_text_lines()[0]), item.item_id
        assert not any(_QUESTION_NUMBER.match(line) for line in qti[item.item_id].prompt_lines)
        assert item.plain_text_lines()[0] in paragraphs
