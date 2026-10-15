"""Exam.net QTI export of recorded conversions: matching lists, distractors and parent layout."""

import hashlib
import io
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiItem,
    ExamNetQtiPackageStatus,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_item_xml import (
    serialize_qti_assessment_item,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_package import (
    build_examnet_qti_package_plan,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_validation import (
    build_examnet_qti_validation_report,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_xml import QTI_NAMESPACE
from skriptoteket.domain.curated_apps.exam_workspace.examnet_qti_export import (
    native_exam_to_examnet_qti_items,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeAssetSegment,
    NativeExamAsset,
    NativeExamDocument,
    NativeExamDocumentOrigin,
    NativeExamItem,
    NativeExamItemKind,
    NativeMatchRight,
    NativeParagraph,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_qti_writer import (
    ExamNetQtiPackageWriter,
)
from tests.unit.domain.curated_apps.exam_workspace.recorded_native_exam_support import (
    item_numbers,
    parent_over,
    recorded_document,
    recorded_items,
)

_BASELINE = json.loads(
    Path("tests/fixtures/exam_conversion/qti_standalone_item_xml_sha256.json").read_text()
)
_INSTRUCTION = "Complete every item in this part."
_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108040000"
    "00b51c0c020000000b4944415478da636ffcff1f0003030200efbfa7db0000000049454e44ae426082"
)


def _tag(local_name: str) -> str:
    return f"{{{QTI_NAMESPACE}}}{local_name}"


def _root(item: ExamNetQtiItem, image_paths: tuple[str, ...] = ()) -> ElementTree.Element:
    return ElementTree.fromstring(serialize_qti_assessment_item(item, image_paths=image_paths))


def _items_of_kind(kind: NativeExamItemKind) -> list[int]:
    return item_numbers(recorded_items(), kind)


def _run(kind: NativeExamItemKind, length: int) -> tuple[int, ...]:
    numbers = _items_of_kind(kind)
    for start in range(len(numbers) - length + 1):
        window = numbers[start : start + length]
        if window == list(range(window[0], window[0] + length)):
            return tuple(window)
    raise AssertionError("recording has no such run")


def _matching_qti_items(document: NativeExamDocument) -> list[ExamNetQtiItem]:
    return [
        item
        for item in native_exam_to_examnet_qti_items(document)
        if item.source_item_type == NativeExamItemKind.MATCHING.value
    ]


def _lists(root: ElementTree.Element) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    (interaction,) = root.iter(_tag("qti-match-interaction"))
    left, right = interaction.findall(_tag("qti-simple-match-set"))
    return (
        [(c.attrib["identifier"], c.text or "") for c in left],
        [(c.attrib["identifier"], c.text or "") for c in right],
    )


def _correct_pairs(
    root: ElementTree.Element, response_id: str = "RESPONSE"
) -> set[tuple[str, str]]:
    declaration = next(
        d
        for d in root.iter(_tag("qti-response-declaration"))
        if d.attrib["identifier"] == response_id
    )
    values = declaration.findall(f"{_tag('qti-correct-response')}/{_tag('qti-value')}")
    pairs = [(v.text or "").split() for v in values]
    return {(left, right) for left, right in pairs}


def _package(items: tuple[ExamNetQtiItem, ...]) -> tuple[zipfile.ZipFile, str]:
    plan = build_examnet_qti_package_plan(package_name="recorded", items=items)
    assert plan.status is ExamNetQtiPackageStatus.PASSED, plan.warnings
    package = ExamNetQtiPackageWriter().build_package_bytes(plan)
    report = build_examnet_qti_validation_report(
        plan=plan, package_filename="recorded.zip", package_bytes=package
    )
    return zipfile.ZipFile(io.BytesIO(package)), report.package_status.value


# --- standalone items -------------------------------------------------------------------


@pytest.mark.parametrize("exam", sorted(_BASELINE))
def test_recorded_standalone_items_serialize_to_the_current_exporter_bytes(exam: str):
    """Each converted item's standalone XML is fixed for the fresh v14 recordings."""
    mismatched = []
    for item in recorded_items(exam):
        expected = _BASELINE[exam].get(f"{item.sequence:03d}")
        if expected is None:
            continue
        single = item.model_copy(update={"sequence": 1})
        document = recorded_document(items=(single,))
        (qti,) = native_exam_to_examnet_qti_items(document)
        if hashlib.sha256(serialize_qti_assessment_item(qti)).hexdigest() != expected:
            mismatched.append(item.item_id)
    assert not mismatched
    assert len(_BASELINE[exam]) >= 8


@pytest.mark.parametrize("exam", sorted(_BASELINE))
def test_a_parents_child_serializes_byte_for_byte_as_the_same_item_standalone(exam: str):
    """The parent layout wraps children without changing any child's own XML."""
    items = recorded_items(exam)
    standalone = {
        item.item_id: item
        for item in native_exam_to_examnet_qti_items(recorded_document(items=items))
    }
    checked: set[NativeExamItemKind] = set()
    for start in range(len(items) - 1):
        window = items[start : start + 2]
        kind = window[0].kind
        if window[1].kind is not kind or kind in checked:
            continue
        checked.add(kind)
        parent = parent_over("parent_001", _INSTRUCTION, *(item.sequence for item in window))
        document = recorded_document((parent,), items=items)
        (exported,) = [item for item in native_exam_to_examnet_qti_items(document) if item.children]
        assert [child.item_id for child in exported.children] == [
            item.item_id for item in window
        ], (exam, kind)
        for child in exported.children:
            assert serialize_qti_assessment_item(child) == serialize_qti_assessment_item(
                standalone[child.item_id]
            ), (exam, child.item_id)
    assert checked


# --- matching lists (F1) and distractors (D7) -------------------------------------------


def test_matching_lists_export_in_native_order_and_index_pairing_does_not_reveal_the_key():
    document = recorded_document()
    native = {item.item_id: item for item in document.items}
    qti_matching = _matching_qti_items(document)

    assert len(qti_matching) == 3
    for qti in qti_matching:
        item = native[qti.item_id]
        left, right = _lists(_root(qti))

        assert [text for _, text in left] == [entry.text for entry in item.match_left]
        assert [text for _, text in right] == [entry.text for entry in item.match_right]
        assert set(zip((i for i, _ in left), (i for i, _ in right), strict=True)) != _correct_pairs(
            _root(qti)
        )
        assert _correct_pairs(_root(qti)) == {
            (pair.left_id, pair.right_id) for pair in item.answer_key.match_pairs
        }


def test_unpaired_right_entry_is_listed_in_its_place_and_is_not_part_of_the_key():
    items = recorded_items()
    target = next(item for item in items if item.kind is NativeExamItemKind.MATCHING)
    distractor = NativeMatchRight(right_id="right_099", text="An entry nobody pairs")
    widened = NativeExamItem.model_validate(
        {
            **dict(target),
            "match_right": (target.match_right[0], distractor, *target.match_right[1:]),
        }
    )
    document = recorded_document(
        items=tuple(widened if item.item_id == target.item_id else item for item in items)
    )

    (qti,) = (q for q in _matching_qti_items(document) if q.item_id == target.item_id)
    root = _root(qti)
    left, right = _lists(root)

    assert right[1] == ("right_099", "An entry nobody pairs")
    assert len(right) == len(left) + 1
    assert "right_099" not in {identifier for pair in _correct_pairs(root) for identifier in pair}
    mapping_keys = {e.attrib["map-key"] for e in root.iter(_tag("qti-map-entry"))}
    assert not any("right_099" in key for key in mapping_keys)
    (interaction,) = root.iter(_tag("qti-match-interaction"))
    assert interaction.attrib["max-associations"] == str(len(left))
    _, status = _package((qti,))
    assert status == "passed"


# --- parents ----------------------------------------------------------------------------


def _parent_document(kind: NativeExamItemKind, length: int):
    numbers = _run(kind, length)
    return numbers, recorded_document((parent_over("parent_001", _INSTRUCTION, *numbers),))


def test_parent_of_recorded_gap_fill_children_is_one_item_with_a_separator_before_each_sentence():
    numbers, document = _parent_document(NativeExamItemKind.GAP_FILL, 6)
    native = document.items
    items = native_exam_to_examnet_qti_items(document)

    assert len(items) == len(native) - len(numbers) + 1
    (parent,) = (item for item in items if item.children)
    assert parent.item_id == "parent_001"
    assert parent.sequence == numbers[0]
    assert [child.item_id for child in parent.children] == [f"item_{n:03d}" for n in numbers]
    assert parent.max_score == sum(child.max_score or 0 for child in parent.children)

    root = _root(parent)
    body = root.find(_tag("qti-item-body"))
    assert body is not None
    blocks = list(body)
    assert blocks[0].tag == _tag("p") and blocks[0].text == _INSTRUCTION
    after = blocks[1:]
    separators = [b for b in after if b.tag == _tag("qti-gap-match-interaction")]
    assert [s.attrib["response-identifier"] for s in separators] == [
        f"item_{n:03d}_SEPARATOR" for n in numbers
    ]
    # every separator is directly followed by that child's own sentence, and each sentence
    # is directly preceded by a separator
    for index, block in enumerate(after):
        if block.tag == _tag("qti-gap-match-interaction"):
            sentence = after[index + 1]
            child_id = block.attrib["response-identifier"].removesuffix("_SEPARATOR")
            entries = sentence.findall(_tag("qti-text-entry-interaction"))
            assert entries
            assert all(e.attrib["response-identifier"].startswith(f"{child_id}_") for e in entries)
        elif block.tag == _tag("p"):
            assert after[index - 1].tag == _tag("qti-gap-match-interaction") or after[
                index - 1
            ].tag == _tag("p")
    entry_ids = [
        e.attrib["response-identifier"] for e in root.iter(_tag("qti-text-entry-interaction"))
    ]
    assert (
        len(entry_ids)
        == len(set(entry_ids))
        == sum(len(c.text_entry_gaps) for c in parent.children)
    )

    declarations = {d.attrib["identifier"]: d for d in root.iter(_tag("qti-response-declaration"))}
    for separator in separators:
        declaration = declarations[separator.attrib["response-identifier"]]
        assert declaration.attrib["cardinality"] == "multiple"
        assert declaration.attrib["base-type"] == "directedPair"
        assert len(declaration) == 0
    for entry_id in entry_ids:
        assert declarations[entry_id].find(_tag("qti-mapping")) is not None
        assert (
            declarations[entry_id].find(f"{_tag('qti-correct-response')}/{_tag('qti-value')}")
            is not None
        )
    _assert_guarded_mapped_scores(root, entry_ids)
    outcomes = {o.attrib["identifier"]: o for o in root.iter(_tag("qti-outcome-declaration"))}
    max_score_value = outcomes["MAXSCORE"].find(f".//{_tag('qti-value')}")
    assert max_score_value is not None
    assert max_score_value.text == str(parent.max_score)


def test_package_with_a_gap_fill_parent_replaces_its_children_where_the_first_child_stood():
    numbers, document = _parent_document(NativeExamItemKind.GAP_FILL, 6)
    archive, status = _package(native_exam_to_examnet_qti_items(document))

    names = archive.namelist()
    assert status == "passed"
    assert "items/parent_001.xml" in names
    assert not any(f"items/item_{n:03d}.xml" in names for n in numbers)
    refs = [
        r.attrib["href"]
        for r in ElementTree.fromstring(archive.read("assessment.xml")).iter(
            _tag("qti-assessment-item-ref")
        )
    ]
    assert refs[numbers[0] - 1] == "items/parent_001.xml"
    assert len(refs) == len(document.items) - len(numbers) + 1


def test_parent_of_recorded_choice_children_holds_each_stem_in_its_own_interaction():
    numbers, document = _parent_document(NativeExamItemKind.SINGLE_CHOICE, 4)
    items = native_exam_to_examnet_qti_items(document)
    (parent,) = (item for item in items if item.children)
    archive, status = _package(items)
    assert status == "passed"

    root = _root(parent)
    body = root.find(_tag("qti-item-body"))
    assert body is not None
    blocks = list(body)
    assert [b.tag for b in blocks] == [_tag("p")] + [_tag("qti-choice-interaction")] * len(numbers)
    assert blocks[0].text == _INSTRUCTION
    prompts = []
    for block in blocks[1:]:
        prompt = block.find(_tag("qti-prompt"))
        assert prompt is not None
        prompts.append("".join(prompt.itertext()).strip())
    assert all(prompts) and len(set(prompts)) == len(prompts)
    assert [b.attrib["response-identifier"] for b in blocks[1:]] == [
        f"item_{n:03d}_RESPONSE" for n in numbers
    ]
    _assert_guarded_mapped_scores(root, [f"item_{n:03d}_RESPONSE" for n in numbers])
    response_processing = root.find(_tag("qti-response-processing"))
    assert response_processing is not None
    assert response_processing.attrib.get("template") is None
    assert archive.read("items/parent_001.xml")


def _assert_guarded_mapped_scores(root: ElementTree.Element, response_ids: list[str]) -> None:
    processing = root.find(_tag("qti-response-processing"))
    assert processing is not None
    initial = processing.find(_tag("qti-set-outcome-value"))
    assert initial is not None
    assert initial.attrib == {"identifier": "SCORE"}
    initial_value = initial.find(_tag("qti-base-value"))
    assert initial_value is not None
    assert initial_value.attrib == {"base-type": "float"}
    assert initial_value.text == "0"
    conditions = processing.findall(f"{_tag('qti-response-condition')}/{_tag('qti-response-if')}")
    assert len(conditions) == len(response_ids)
    for condition, response_id in zip(conditions, response_ids, strict=True):
        predicate = condition.find(
            f"{_tag('qti-not')}/{_tag('qti-is-null')}/{_tag('qti-variable')}"
        )
        assert predicate is not None
        assert predicate.attrib == {"identifier": response_id}
        addition = condition.find(_tag("qti-set-outcome-value"))
        assert addition is not None
        assert addition.attrib == {"identifier": "SCORE"}
        previous_score = addition.find(f"{_tag('qti-sum')}/{_tag('qti-variable')}")
        assert previous_score is not None
        assert previous_score.attrib == {"identifier": "SCORE"}
        mapped_score = addition.find(f"{_tag('qti-sum')}/{_tag('qti-map-response')}")
        assert mapped_score is not None
        assert mapped_score.attrib == {"identifier": response_id}


def test_parent_of_recorded_matching_children_keeps_each_item_lists_in_native_order():
    numbers, document = _parent_document(NativeExamItemKind.MATCHING, 3)
    native = {item.item_id: item for item in document.items}
    items = native_exam_to_examnet_qti_items(document)
    (parent,) = (item for item in items if item.children)
    _, status = _package(items)
    assert status == "passed"

    root = _root(parent)
    interactions = list(root.iter(_tag("qti-match-interaction")))
    assert len(interactions) == len(numbers)
    for number, interaction in zip(numbers, interactions, strict=True):
        item = native[f"item_{number:03d}"]
        right = interaction.findall(_tag("qti-simple-match-set"))[1]
        assert [c.text for c in right] == [e.text for e in item.match_right]
        assert _correct_pairs(root, f"item_{number:03d}_RESPONSE") == {
            (pair.left_id, pair.right_id) for pair in item.answer_key.match_pairs
        }


def test_parent_with_one_child_folds_its_instruction_into_the_childs_prompt():
    (number,) = _run(NativeExamItemKind.SINGLE_CHOICE, 1)
    document = recorded_document((parent_over("parent_001", _INSTRUCTION, number),))
    items = native_exam_to_examnet_qti_items(document)
    (folded,) = (item for item in items if item.item_id == "parent_001")
    archive, status = _package(items)

    assert status == "passed"
    assert not folded.children
    prompt = _root(folded).find(f".//{_tag('qti-prompt')}")
    assert prompt is not None
    assert [p.text for p in prompt.findall(_tag("p"))][0] == _INSTRUCTION
    assert "items/parent_001.xml" in archive.namelist()


def test_images_of_parent_children_stay_with_their_own_child():
    numbers = _run(NativeExamItemKind.SINGLE_CHOICE, 2)
    payloads = {"asset_00000000000000a1": _PNG, "asset_00000000000000b2": _PNG + b"\x00"}
    items = recorded_items()
    imaged = []
    for sequence, (number, asset_id) in enumerate(zip(numbers, payloads, strict=True), start=1):
        item = items[number - 1]
        imaged.append(
            NativeExamItem.model_validate(
                {
                    **dict(item),
                    "item_id": f"item_{sequence:03d}",
                    "sequence": sequence,
                    "body": (
                        *item.body,
                        NativeParagraph(segments=(NativeAssetSegment(asset_id=asset_id),)),
                    ),
                }
            )
        )
    document = NativeExamDocument(
        document_id=recorded_document().document_id,
        revision=1,
        title="Recorded exam",
        items=tuple(imaged),
        parents=(parent_over("parent_001", _INSTRUCTION, 1, 2),),
        assets=tuple(
            NativeExamAsset(
                asset_id=asset_id,
                sha256=hashlib.sha256(payload).hexdigest(),
                media_type="image/png",
                byte_length=len(payload),
            )
            for asset_id, payload in payloads.items()
        ),
        origin=NativeExamDocumentOrigin(kind="created"),
    )
    items_out = native_exam_to_examnet_qti_items(document, assets_by_id=payloads)
    (parent,) = items_out
    archive, status = _package(items_out)

    assert status == "passed"
    images = sorted(n for n in archive.namelist() if n.startswith("items/images/"))
    assert len(images) == 2
    image_srcs = tuple(name.removeprefix("items/") for name in images)
    sources = [
        [img.attrib["src"] for img in prompt.iter(_tag("img"))]
        for prompt in _root(parent, image_srcs).iter(_tag("qti-prompt"))
    ]
    assert sources == [[image_srcs[0]], [image_srcs[1]]]
    assert archive.read(images[0]) != archive.read(images[1])
