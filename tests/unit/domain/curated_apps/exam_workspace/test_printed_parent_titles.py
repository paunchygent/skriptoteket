"""Parent titles span the children's printed labels, not Exam.net running numbers (D20).

The exams are converted from a recorded live run whose items carry printed labels. The
expected title is the question part of gold's own parent label, such as "Question 1–7" in
"Part 3, Question 1–7", so the check holds for every recorded exam without naming one.
Running numbers continue across parts; printed numbers restart, so the two differ.
"""

import hashlib
import re
from pathlib import Path
from xml.etree import ElementTree

import pytest

from scripts.exam_conversion_eval.gold import GoldParent
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_item_xml import (
    serialize_qti_assessment_item,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_language_labels import (
    exam_language_labels,
)
from skriptoteket.domain.curated_apps.exam_workspace.examnet_qti_export import (
    native_exam_to_examnet_qti_items,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeAssetSegment,
    NativeExamAsset,
    NativeParagraph,
)
from tests.unit.scripts.exam_conversion_corpus_support import gold_exam, replayed

_LABELLED = Path("tests/fixtures/exam_conversion/docx_build_v9")
_STEMS = tuple(sorted(path.name for path in _LABELLED.iterdir() if path.is_dir()))


def _parent_titles(stem: str) -> list[tuple[str, str, str]]:
    """(QTI title, gold's printed span, running-number span) for each parent, in order."""
    document, _ = replayed(stem, _LABELLED)
    gold_parents = [item for item in gold_exam(stem).items if isinstance(item, GoldParent)]
    assert len(document.parents) == len(gold_parents), stem
    titles = {item.item_id: item.title for item in native_exam_to_examnet_qti_items(document)}
    rows: list[tuple[str, str, str]] = []
    for parent, gold in zip(document.parents, gold_parents, strict=True):
        first = document.item_by_id(parent.item_ids[0])
        last = document.item_by_id(parent.item_ids[-1])
        word = gold.source_label.split(",")[-1].split()[0]
        running = f"{word} {first.sequence}–{last.sequence}"
        rows.append((titles[parent.parent_id], gold.source_label.split(",")[-1].strip(), running))
    return rows


@pytest.mark.parametrize("stem", _STEMS)
def test_parent_titles_are_the_printed_span(stem: str) -> None:
    for title, printed, _ in _parent_titles(stem):
        assert title == printed, stem


@pytest.mark.parametrize("stem", _STEMS)
def test_every_child_of_a_parent_keeps_a_printed_label(stem: str) -> None:
    document, _ = replayed(stem, _LABELLED)
    for parent in document.parents:
        assert all(document.item_by_id(item_id).printed_label for item_id in parent.item_ids)


def test_the_recordings_hold_a_part_whose_numbering_restarts() -> None:
    restarted = [
        (stem, printed, running)
        for stem in _STEMS
        for _, printed, running in _parent_titles(stem)
        if printed != running
    ]
    assert restarted


@pytest.mark.parametrize("stem", _STEMS)
def test_printed_labels_never_enter_student_visible_text(stem: str) -> None:
    document, _ = replayed(stem, _LABELLED)
    numbered = [item for item in document.items if re.search(r"\d", item.printed_label or "")]
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
def test_an_untitled_item_keeps_its_running_title_and_an_unnumbered_image_alt(stem: str) -> None:
    """A printed label titles only parents; an image added to the item never names it."""
    document, _ = replayed(stem, _LABELLED)
    labels = exam_language_labels(document)
    untitled = [item for item in document.items if not item.title and item.printed_label]
    assert untitled
    if stem == "bf26_english_1_unit_test_kap_1_2_med_facit":
        (restarted,) = [item for item in untitled if item.sequence == 28]
        assert restarted.printed_label == "1"
        assert labels.image == "Image"
    for item in untitled:
        assert labels.item_title(item) == labels.question_label(item.sequence), item.printed_label
        illustrated = item.model_copy(
            update={
                "body": (
                    *item.body,
                    NativeParagraph(segments=(NativeAssetSegment(asset_id=_ASSET.asset_id),)),
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
        if document.parent_of(item.item_id) is None:
            assert qti.title == labels.question_label(item.sequence), (stem, item.printed_label)
        xml = ElementTree.fromstring(serialize_qti_assessment_item(qti, image_paths=("image.png",)))
        body = xml.find("{*}itemBody")
        assert body is not None
        alts = [node.attrib["alt"] for node in body.iter() if node.tag.endswith("}img")]
        assert alts == [f"{labels.image} 1"], (stem, item.printed_label)
        for alt in alts:
            assert labels.question_label(item.printed_label or "") not in alt
            assert labels.question_label(item.sequence) not in alt
