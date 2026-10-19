"""Parent titles span the children's printed labels, not Exam.net running numbers (D20).

The exams are converted from the fresh live recordings; each parent's QTI title is the span
of its children's printed labels, which restart across parts while the running numbers
continue. Item titles stay the running question label, and an added image gets an alt text
that never names a question.
"""

import hashlib
import re
from dataclasses import dataclass
from xml.etree import ElementTree

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_item_xml import (
    serialize_qti_assessment_item,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_language_labels import (
    SWEDISH_EXAM_LABELS,
)
from skriptoteket.domain.curated_apps.exam_workspace.examnet_qti_export import (
    native_exam_to_examnet_qti_items,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeAssetSegment,
    NativeParagraph,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamAsset,
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import (
    NativeExamParent,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeParseOrigin,
)
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import build_replay
from tests.unit.domain.curated_apps.exam_workspace.recorded_build_events_support import (
    unexpected_build_events,
)

_GRAMMAR_1 = "svenska_2_grammatik_omprov_variant_1_med_facit"
_GRAMMAR_2 = "svenska_2_grammatik_omprov_variant_2_med_facit"
_POETRY = "chapter_4_poetry_and_lyrics_quiz_med_facit"
_STEMS = (_GRAMMAR_1, _GRAMMAR_2, _POETRY)
_RESTARTED = "body:0111"


@dataclass(frozen=True)
class _Build:
    document: NativeExamDocument

    def item(self, anchor: str) -> NativeExamItem:
        return next(item for item in self.document.items if item.source_anchor == anchor)

    def parent_of(self, anchor: str) -> NativeExamParent | None:
        return self.document.parent_of(self.item(anchor).item_id)

    def children(self, parent: NativeExamParent) -> list[NativeExamItem]:
        return [self.document.item_by_id(item_id) for item_id in parent.item_ids]


_BUILDS: dict[str, _Build] = {}


async def _build(exam: str) -> _Build:
    if exam not in _BUILDS:
        replay = build_replay(exam)
        outcome = await replay.pipeline.convert(job=replay.job())
        assert not unexpected_build_events(exam, outcome.result.events), exam
        _BUILDS[exam] = _Build(outcome.result.document)
    return _BUILDS[exam]


def _titles(document: NativeExamDocument) -> dict[str, str]:
    return {item.item_id: item.title for item in native_exam_to_examnet_qti_items(document)}


@pytest.mark.parametrize("stem", _STEMS)
async def test_parent_titles_span_the_childrens_printed_labels(stem: str):
    build = await _build(stem)
    document = build.document
    labels = SWEDISH_EXAM_LABELS
    titles = _titles(document)

    assert document.parents
    for parent in document.parents:
        children = build.children(parent)
        assert all(child.printed_label for child in children), stem
        assert titles[parent.parent_id] == labels.printed_span(
            children[0].printed_label or "", children[-1].printed_label or ""
        ), stem


async def test_a_part_whose_numbering_restarts_titles_the_printed_span_not_the_running_numbers():
    build = await _build(_POETRY)
    document = build.document
    labels = SWEDISH_EXAM_LABELS
    parent = build.parent_of(_RESTARTED)
    assert parent is not None
    children = build.children(parent)
    titles = _titles(document)

    running = labels.question_label(children[0].sequence, children[-1].sequence)
    printed = labels.printed_span(children[0].printed_label or "", children[-1].printed_label or "")
    assert running == "Fråga 22–28"
    assert printed == "Question 1–7"
    assert titles[parent.parent_id] == printed != running


@pytest.mark.parametrize("stem", _STEMS)
async def test_printed_labels_never_enter_student_visible_text(stem: str):
    build = await _build(stem)
    document = build.document
    # D9 of TASK-SKRIPT-39-04-17: a source-review item shows the question as printed.
    numbered = [
        item
        for item in document.items
        if re.search(r"\d", item.printed_label or "")
        and item.review.parse_origin is not NativeParseOrigin.SOURCE_FALLBACK
    ]
    assert numbered
    for item in numbered:
        label = re.compile(rf"^\s*{re.escape(item.printed_label or '')}\b")
        assert not any(label.match(line) for line in item.plain_text_lines()), (stem, item)


_PNG = b"\x89PNG\r\n\x1a\nimage-bytes"
_ASSET = NativeExamAsset(
    asset_id="asset_0123456789abcdef",
    sha256=hashlib.sha256(_PNG).hexdigest(),
    media_type="image/png",
    byte_length=len(_PNG),
)


@pytest.mark.parametrize("stem", _STEMS)
async def test_every_item_keeps_its_running_title_and_an_unnumbered_image_alt(stem: str):
    """No item carries a printed title (39-05-08): its QTI title is its running question
    label, a printed label titles only parents, and an image added to the item never
    names it."""
    build = await _build(stem)
    document = build.document
    labels = SWEDISH_EXAM_LABELS
    untitled = [item for item in document.items if item.printed_label]
    assert untitled

    for item in untitled:
        (single,) = native_exam_to_examnet_qti_items(
            document.model_copy(update={"items": (item,), "parents": ()})
        )
        assert single.title == labels.question_label(item.sequence), (stem, item.printed_label)

        illustrated = item.model_copy(
            update={
                "body": (
                    *item.body,
                    NativeParagraph(
                        heading_level=None, segments=(NativeAssetSegment(asset_id=_ASSET.asset_id),)
                    ),
                )
            }
        )
        changed = document.model_copy(
            update={
                "items": tuple(illustrated if i is item else i for i in document.items),
                "assets": (_ASSET,),
            }
        )
        exported = native_exam_to_examnet_qti_items(changed, assets_by_id={_ASSET.asset_id: _PNG})
        (qti,) = [entry for entry in exported if entry.image_resources]
        xml = ElementTree.fromstring(serialize_qti_assessment_item(qti, image_paths=("image.png",)))
        body = xml.find("{*}qti-item-body")
        assert body is not None
        alts = [node.attrib["alt"] for node in body.iter() if node.tag.endswith("}img")]
        assert alts == [f"{labels.image} 1"], (stem, item.printed_label)
        for alt in alts:
            assert labels.question_label(item.printed_label or "") not in alt
            assert labels.question_label(item.sequence) not in alt
