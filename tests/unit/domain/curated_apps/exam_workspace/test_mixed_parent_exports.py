"""Exports of a recorded parent whose children differ in kind (D27).

A parent holds any mix of question types, as an Exam.net information block does. QTI exports
it as one assessment item with one interaction per child, each child with its own response
and mapping, and SCORE sums every child's mapped responses. PDF and DOCX print the
instruction once, before the first child, and each child as its own kind.
"""

import io
import zipfile
from xml.etree import ElementTree

from docx import Document

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_examnet_pdf_contracts import (
    DigiExamExamNetPdfStatus,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiExamNetProofStatus,
    ExamNetQtiInteractionType,
    ExamNetQtiItem,
    ExamNetQtiPackageStatus,
    ExamNetQtiTargetSupportStatus,
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
from skriptoteket.domain.curated_apps.exam_workspace.examnet_pdf_export import (
    native_exam_to_pdf_document,
)
from skriptoteket.domain.curated_apps.exam_workspace.examnet_qti_export import (
    native_exam_to_examnet_qti_items,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeAnswerKey,
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_writer import (  # noqa: E501
    ExamWorkspaceDocxWriter,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_qti_writer import (
    ExamNetQtiPackageWriter,
)
from tests.unit.domain.curated_apps.exam_workspace.recorded_native_exam_support import (
    parent_over,
    recorded_document,
    recorded_items,
)

_INSTRUCTION = "Answer every question in this part."
_INTERACTION_BY_KIND = {
    NativeExamItemKind.SINGLE_CHOICE: "choiceInteraction",
    NativeExamItemKind.MULTIPLE_RESPONSE: "choiceInteraction",
    NativeExamItemKind.MATCHING: "matchInteraction",
    NativeExamItemKind.FREE_TEXT: "extendedTextInteraction",
}


def _tag(local_name: str) -> str:
    return f"{{{QTI_NAMESPACE}}}{local_name}"


def _mixed_window() -> tuple[int, ...]:
    """The first five consecutive recorded items holding a gap fill, a matching and a choice."""
    items = recorded_items()
    wanted = {NativeExamItemKind.GAP_FILL, NativeExamItemKind.MATCHING}
    for start in range(len(items) - 4):
        window = items[start : start + 5]
        kinds = {item.kind for item in window}
        if wanted <= kinds and NativeExamItemKind.SINGLE_CHOICE in kinds:
            return tuple(item.sequence for item in window)
    raise AssertionError("recording has no mixed window")


def _mixed_parent() -> tuple[tuple[int, ...], tuple[ExamNetQtiItem, ...], ExamNetQtiItem]:
    numbers = _mixed_window()
    document = recorded_document((parent_over("parent_001", _INSTRUCTION, *numbers),))
    items = native_exam_to_examnet_qti_items(document)
    (parent,) = (item for item in items if item.children)
    return numbers, items, parent


def test_mixed_parent_is_one_item_with_one_interaction_per_child_in_order():
    numbers, items, parent = _mixed_parent()
    native = {item.item_id: item for item in recorded_items()}
    kinds = [native[f"item_{n:03d}"].kind for n in numbers]

    assert len(items) == len(native) - len(numbers) + 1
    assert [child.item_id for child in parent.children] == [f"item_{n:03d}" for n in numbers]
    assert len(set(kinds)) == 3
    root = ElementTree.fromstring(serialize_qti_assessment_item(parent, image_paths=()))
    body = root.find(_tag("itemBody"))
    assert body is not None
    blocks = list(body)
    assert blocks[0].tag == _tag("p") and blocks[0].text == _INSTRUCTION
    owners = []
    for block in blocks[1:]:
        identifier = block.attrib.get("responseIdentifier")
        if identifier is not None:
            owners.append((block.tag, identifier))
    expected = []
    for number, kind in zip(numbers, kinds, strict=True):
        child_id = f"item_{number:03d}"
        if kind is NativeExamItemKind.GAP_FILL:
            expected.append((_tag("gapMatchInteraction"), f"{child_id}_SEPARATOR"))
        else:
            expected.append((_tag(_INTERACTION_BY_KIND[kind]), f"{child_id}_RESPONSE"))
    assert owners == expected


def test_each_mixed_child_keeps_its_own_response_and_mapping_and_score_sums_them():
    numbers, _, parent = _mixed_parent()
    root = ElementTree.fromstring(serialize_qti_assessment_item(parent, image_paths=()))
    declarations = {d.attrib["identifier"]: d for d in root.iter(_tag("responseDeclaration"))}
    mapped: list[str] = []
    for number, child in zip(numbers, parent.children, strict=True):
        child_id = f"item_{number:03d}"
        if child.interaction_type is ExamNetQtiInteractionType.GAP_FILL:
            entries = [
                identifier
                for identifier in declarations
                if identifier.startswith(f"{child_id}_") and identifier != f"{child_id}_SEPARATOR"
            ]
            assert len(entries) == len(child.text_entry_gaps)
        else:
            entries = [f"{child_id}_RESPONSE"]
        for identifier in entries:
            declaration = declarations[identifier]
            assert declaration.find(f"{_tag('correctResponse')}/{_tag('value')}") is not None
            assert declaration.find(_tag("mapping")) is not None
        mapped.extend(entries)
    assert {
        declarations[f"item_{numbers[k]:03d}_RESPONSE"].attrib["baseType"]
        for k, child in enumerate(parent.children)
        if child.interaction_type is not ExamNetQtiInteractionType.GAP_FILL
    } == {"directedPair", "identifier"}

    summed = [
        m.attrib["identifier"] for m in root.iterfind(f".//{_tag('sum')}/{_tag('mapResponse')}")
    ]
    assert summed == mapped
    (score,) = (s for s in root.iter(_tag("setOutcomeValue")) if s.attrib["identifier"] == "SCORE")
    assert score.find(_tag("sum")) is not None
    assert parent.max_score == sum(child.max_score or 0 for child in parent.children)
    outcomes = {o.attrib["identifier"]: o for o in root.iter(_tag("outcomeDeclaration"))}
    max_score = outcomes["MAXSCORE"].find(f".//{_tag('value')}")
    assert max_score is not None and max_score.text == str(parent.max_score)


def test_package_with_a_mixed_parent_passes_and_is_gated_by_any_child_interaction():
    _, items, _ = _mixed_parent()

    plan = build_examnet_qti_package_plan(package_name="recorded", items=items)
    assert plan.status is ExamNetQtiPackageStatus.PASSED, plan.warnings
    assert plan.target_support_status is ExamNetQtiTargetSupportStatus.PROOF_GATED
    assert plan.examnet_proof_status is ExamNetQtiExamNetProofStatus.NOT_PROVEN
    package = ExamNetQtiPackageWriter().build_package_bytes(plan)
    report = build_examnet_qti_validation_report(
        plan=plan, package_filename="recorded.zip", package_bytes=package
    )
    assert report.package_status.value == "passed"
    assert zipfile.ZipFile(io.BytesIO(package)).read("items/parent_001.xml")


def test_package_status_reads_a_gated_child_behind_a_choice_first_child():
    items = recorded_items()
    choice = next(i.sequence for i in items if i.kind is NativeExamItemKind.SINGLE_CHOICE)
    gap = next(
        i.sequence for i in items if i.kind is NativeExamItemKind.GAP_FILL and i.sequence > choice
    )
    document = recorded_document(
        (parent_over("parent_001", _INSTRUCTION, *range(choice, gap + 1)),)
    )
    exported = native_exam_to_examnet_qti_items(document)
    only_parent = tuple(item for item in exported if item.children)
    (parent,) = only_parent
    assert parent.children[0].interaction_type is ExamNetQtiInteractionType.SINGLE_CHOICE

    plan = build_examnet_qti_package_plan(package_name="recorded", items=only_parent)

    assert plan.target_support_status is ExamNetQtiTargetSupportStatus.PROOF_GATED
    assert plan.examnet_proof_status is ExamNetQtiExamNetProofStatus.NOT_PROVEN


def test_pdf_and_docx_print_a_mixed_parent_instruction_once_before_its_first_child():
    numbers = _mixed_window()
    document = recorded_document((parent_over("parent_001", _INSTRUCTION, *numbers),))
    children = [document.item_by_id(f"item_{n:03d}") for n in numbers]
    assert len({child.kind for child in children}) == 3
    opening = children[0].plain_text_lines()[0]

    pdf = native_exam_to_pdf_document(document)
    assert pdf.status is DigiExamExamNetPdfStatus.SUCCESS, pdf.warnings
    assert pdf.html.count(_INSTRUCTION) == 1
    first_section = pdf.html.index(f"<h2>Fråga {numbers[0]}</h2>")
    second_section = pdf.html.index(f"<h2>Fråga {numbers[1]}</h2>")
    assert first_section < pdf.html.index(_INSTRUCTION) < second_section

    writer = ExamWorkspaceDocxWriter()
    content = writer.build_docx_bytes(document)
    writer.validate_docx_bytes(content, expected_item_count=len(document.items))
    lines = [p.text for p in Document(io.BytesIO(content)).paragraphs]
    assert lines.count(_INSTRUCTION) == 1
    opening_at = next(k for k, line in enumerate(lines) if opening in line)
    assert lines.index(_INSTRUCTION) < opening_at


def test_a_parent_of_gap_fills_and_one_free_text_passes_package_validation():
    # Gap-fill children carry no prompted interaction, so a parent of gap fills and one
    # free text holds a single prompted interaction; it is still a parent, and its gap
    # sentences before the free text are not a stray stem (staging walk 2026-10-14).
    items = recorded_items()
    gap_fills = [item for item in items if item.kind is NativeExamItemKind.GAP_FILL]
    assert len(gap_fills) >= 3
    free_text = gap_fills[2].model_copy(
        update={
            "kind": NativeExamItemKind.FREE_TEXT,
            "body": (NativeParagraph(segments=(NativeTextSegment(text="Explain why."),)),),
            "gaps": (),
            "answer_key": NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
        }
    )
    kept = (gap_fills[0], gap_fills[1], free_text)
    renumbered = tuple(
        item.model_copy(update={"item_id": f"item_{n:03d}", "sequence": n})
        for n, item in enumerate(kept, start=1)
    )
    document = recorded_document(
        (parent_over("parent_001", _INSTRUCTION, 1, 2, 3),), items=renumbered
    )
    plan = build_examnet_qti_package_plan(
        package_name="mixed", items=native_exam_to_examnet_qti_items(document)
    )
    writer = ExamNetQtiPackageWriter()
    package = writer.build_package_bytes(plan)
    report = build_examnet_qti_validation_report(
        plan=plan, package_filename="mixed.zip", package_bytes=package
    )

    assert report.package_status is ExamNetQtiPackageStatus.PASSED, report.errors
