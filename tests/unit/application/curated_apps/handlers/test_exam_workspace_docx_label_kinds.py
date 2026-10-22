"""Ordering enumeration is gone from the final presentation; part labels stay (D36).

Replays the live recordings of every corpus exam through the production pipeline, then reads
the saved document, the DOCX export and the QTI export. A part label that names a part
inside one question's body reaches all of them as the reply printed it and never becomes the
question's printed label; a choice carries no ordering letter in the document and the DOCX
export adds one letter per choice; a review item shows its source text as printed.

The part-label scenario is built by explicit mutation of a current recorded reply: the
current recordings show model-quality findings outside this contract, so the reply is made
to print two part labels and the test pins the pipeline's and both exports' side of it.
"""

import io
import re
from collections.abc import Callable, Iterator
from xml.etree import ElementTree

import pytest
from docx import Document
from pydantic import JsonValue

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMProviderProfile,
    StructuredLLMRequest,
    StructuredLLMResponse,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import ExamNetQtiItem
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_item_xml import (
    serialize_qti_assessment_item,
)
from skriptoteket.domain.curated_apps.exam_workspace.examnet_qti_export import (
    native_exam_to_examnet_qti_items,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
    NativeItemReviewState,
    NativeParseOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_plain_text
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_writer import (  # noqa: E501
    ExamWorkspaceDocxWriter,
)
from tests.unit.application.curated_apps.handlers.docx_conversion_cache import (
    ConversionCache,
    conversion_cache_fixture,  # noqa: F401 - registers the `conversions` fixture
)
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
    ReplayProvider,
    build_replay,
    recorded_exams,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

_PART_LABEL = re.compile(r"^[a-z]\)\s\S")
_CHOICE_ENUMERATION = re.compile(r"^\s*\(?(?:[A-Za-z]|\d{1,3})[.)]\s")
_CHOICE_KINDS = (NativeExamItemKind.SINGLE_CHOICE, NativeExamItemKind.MULTIPLE_RESPONSE)
_STEP_BOX = "☐"
_MUTATED_EXAM = "bf26_english_1_unit_test_kap_1_2_med_facit"
_MUTATED_BATCH = "docx_w2-10-01"
_MUTATED_ANCHOR = "body:0059"
# The printed inline points of each recorded review item.
_REVIEW_INLINE_POINTS = {
    ("bf26_english_1_unit_test_kap_1_2_med_facit", "item_043"): "(1 p)",
    ("svenska_2_grammatik_omprov_variant_1_med_facit", "item_001"): "(6 p)",
    ("svenska_2_grammatik_omprov_variant_2_med_facit", "item_001"): "(6 p)",
    # REP-0049 rereview F4, decision A: Fråga 5 goes to source review.
    ("svenska_2_grammatik_omprov_variant_2_med_facit", "item_005"): "(6 p)",
}
Corruption = Callable[[dict[str, JsonValue]], None]


async def _document(conversions: ConversionCache, exam: str) -> NativeExamDocument:
    return (await conversions.converted(exam)).outcome.update.document


def _squash(text: str) -> str:
    return " ".join(text.split())


def _leading(line: str) -> str:
    """The first words of a line, enough to find it in a composed export."""
    return _squash(line)[:14]


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


def _first_anchor(entry: JsonValue) -> JsonValue:
    assert isinstance(entry, dict)
    anchors = entry["source_anchors"]
    assert isinstance(anchors, list)
    return anchors[0]


def _entry_at(content: dict[str, JsonValue], anchor: str) -> dict[str, JsonValue]:
    items = content["items"]
    assert isinstance(items, list)
    found = next(i for i in items if _first_anchor(i) == anchor)
    assert isinstance(found, dict)
    return found


def _paragraph(text: str) -> dict[str, JsonValue]:
    return {
        "segments": [
            {
                "kind": "text",
                "text": text,
                "accepted_values": [],
                "asset_id": None,
            }
        ]
    }


def _prefix_first_text(entry: dict[str, JsonValue], text: str) -> None:
    body = entry["body"]
    assert isinstance(body, list) and body
    paragraph = body[0]
    assert isinstance(paragraph, dict)
    segments = paragraph["segments"]
    assert isinstance(segments, list) and segments
    head = segments[0]
    assert isinstance(head, dict)
    original = head["text"]
    assert isinstance(original, str)
    head["text"] = text + original


class _MutatedProvider(ReplayProvider):
    """Serve the recordings, with the reply entry at ``anchor`` changed by ``mutate``."""

    def __init__(self, exam: str, batch: str, anchor: str, mutate: Corruption) -> None:
        super().__init__(exam)
        self._batch = batch
        self._anchor = anchor
        self._mutate = mutate

    async def complete_structured(
        self, *, request: StructuredLLMRequest, profile: StructuredLLMProviderProfile
    ) -> StructuredLLMResponse:
        response = await super().complete_structured(request=request, profile=profile)
        # A converter batch is matched to its recording by anchors, so select the reply by the
        # recording batch that was served, not by the request id.
        if self.recording_ids.get(request.item_id) != self._batch:
            return response
        content = dict(response.content)
        self._mutate(_entry_at(content, self._anchor))
        return StructuredLLMResponse(content, response.finish_reason, response.usage)


async def _mutated_document(
    exam: str, batch: str, anchor: str, mutate: Corruption
) -> NativeExamDocument:
    replay = build_replay(exam, provider=_MutatedProvider(exam, batch, anchor, mutate))
    return (await replay.pipeline.convert(job=replay.job())).update.document


def _print_two_part_labels(entry: dict[str, JsonValue]) -> None:
    """Make the reply print an "a)" stem line and a second "b)" paragraph."""
    _prefix_first_text(entry, "a) ")
    body = entry["body"]
    assert isinstance(body, list)
    entry["body"] = [*body, _paragraph("b) A cooperative spirit answers it.")]


async def test_part_labels_inside_a_body_reach_the_document_and_both_exports_as_printed():
    # A gap_fill stem is built from its source paragraph (TASK-SKRIPT-39-04-16), so the
    # reply-printed labels are tested on a matching item (a choice stem strips a
    # leading enumeration).
    document = await _mutated_document(
        _MUTATED_EXAM, _MUTATED_BATCH, _MUTATED_ANCHOR, _print_two_part_labels
    )
    item = next(item for item in document.items if item.source_anchor == _MUTATED_ANCHOR)
    part_lines = [line for line in item.plain_text_lines() if _PART_LABEL.match(line)]
    paragraphs = _docx_paragraphs(document)
    qti = _qti_items(document)

    assert item.review.parse_origin is NativeParseOrigin.LLM_PARSED
    assert len(part_lines) == 2, "the reply's two part labels did not stay two parts"
    assert _squash(part_lines[0]).startswith(_squash("a) Select the word or phrase"))
    assert _squash(part_lines[1]) == "b) A cooperative spirit answers it."
    # The student DOCX prints an inline gap as a handwriting blank, so the shared part
    # label is the printed fact both exports must keep.
    docx_text = "\n".join(_squash(paragraph) for paragraph in paragraphs)
    for line in part_lines:
        assert _leading(line) in docx_text, f"DOCX export lost {line[:20]!r}"
        assert _leading(line) in _qti_text(qti[item.item_id]), f"QTI export lost {line[:20]!r}"
    assert item.printed_label not in {"a", "b", "a)", "b)"}, "a part label became metadata"


@pytest.mark.parametrize("exam", recorded_exams())
async def test_choices_carry_no_ordering_letter_in_the_document_or_the_qti_export(
    exam: str, conversions: ConversionCache
):
    document = await _document(conversions, exam)
    qti = _qti_items(document)

    for item in document.items:
        if item.kind not in _CHOICE_KINDS:
            continue
        exported = [choice.text for choice in qti[item.item_id].choices]
        assert exported == [_squash(body_plain_text(choice.body)) for choice in item.choices]
        for choice in item.choices:
            assert not _CHOICE_ENUMERATION.match(body_plain_text(choice.body)), (
                item.item_id,
                body_plain_text(choice.body)[:30],
            )


@pytest.mark.parametrize("exam", recorded_exams())
async def test_the_docx_export_adds_one_letter_per_choice_and_never_doubles_it(
    exam: str, conversions: ConversionCache
):
    document = await _document(conversions, exam)
    paragraphs = _docx_paragraphs(document)

    for item in document.items:
        if item.kind not in _CHOICE_KINDS:
            continue
        for index, choice in enumerate(item.choices):
            letter = chr(ord("A") + index)
            assert f"{_STEP_BOX} {letter}) {body_plain_text(choice.body)}" in paragraphs


async def test_a_review_item_shows_its_source_text_as_printed_in_both_exports(
    conversions: ConversionCache,
):
    kept = 0
    visited: set[tuple[str, str]] = set()
    for exam in recorded_exams():
        document = await _document(conversions, exam)
        paragraphs = _docx_paragraphs(document)
        qti = _qti_items(document)
        for item in document.items:
            if item.review.state is not NativeItemReviewState.REVIEW_REQUIRED:
                continue
            kept += 1
            visited.add((exam, item.item_id))
            lines = item.plain_text_lines()
            points = item.points
            for index, line in enumerate(lines):
                expected = line
                if index == len(lines) - 1 and points is not None:
                    expected = line + " " + _REVIEW_INLINE_POINTS[(exam, item.item_id)]
                assert expected in paragraphs, f"{item.item_id}: DOCX export lost {expected[:24]!r}"
                assert _leading(line) in _qti_text(qti[item.item_id]), (
                    f"{item.item_id}: QTI export lost {line[:20]!r}"
                )

    assert kept, "no recorded exam holds a source review item"
    assert visited == set(_REVIEW_INLINE_POINTS), f"review items changed: visited {sorted(visited)}"
