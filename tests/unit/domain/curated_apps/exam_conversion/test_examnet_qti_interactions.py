"""Tests for Exam.net QTI interaction serialization.

Purpose:
    Prove choice, gap-fill, free-text, and matching interactions serialize to
    the expected QTI 3.0 item XML (cardinality, mappings, prompts, scoring),
    ported from Sir Convert-a-Lot at revision 41be61a6.

Relationships:
    - Exercises the exam-conversion QTI item XML and package planning through
      the package writer without service routes or UI behavior.
"""

from __future__ import annotations

import zipfile
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiExamNetProofStatus,
    ExamNetQtiInteractionType,
    ExamNetQtiItem,
    ExamNetQtiTargetSupportStatus,
    ExamNetQtiTextEntryGap,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_package import (
    build_examnet_qti_package_plan,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_xml import (
    MAP_RESPONSE_TEMPLATE,
    QTI_NAMESPACE,
)
from tests.fixtures.exam_conversion_samples import examnet_qti_manual_unkeyed_samples
from tests.unit.domain.curated_apps.exam_conversion.examnet_qti_test_support import (
    build_examnet_qti_zip_bytes,
    item_body_paragraphs,
    json_string,
    keyed_sample,
    read_report,
    write_sample,
)

pytestmark = pytest.mark.unit


def test_choice_packages_encode_single_and_multiple_cardinality(tmp_path: Path) -> None:
    single = write_sample(keyed_sample("single-choice-mcq"), tmp_path)
    multiple = write_sample(keyed_sample("multiple-response-mcq"), tmp_path)

    single_item = _item_root(single / "qti-package.zip")
    multiple_item = _item_root(multiple / "qti-package.zip")

    assert _response_declaration(single_item).attrib["cardinality"] == "single"
    assert _choice_interaction(single_item).attrib["max-choices"] == "1"
    assert _correct_values(single_item) == ["choice_002"]
    assert _response_declaration(multiple_item).attrib["cardinality"] == "multiple"
    assert _choice_interaction(multiple_item).attrib["max-choices"] == "3"
    assert _correct_values(multiple_item) == ["choice_001", "choice_002", "choice_004"]
    assert "shuffle" not in _choice_interaction(single_item).attrib
    assert "shuffle" not in _choice_interaction(multiple_item).attrib
    assert _mapping(single_item).attrib == {
        "default-value": "0",
        "lower-bound": "0",
        "upper-bound": "4",
    }
    assert _map_entry_pairs(single_item) == [("choice_002", "4")]
    assert multiple_item.find(f".//{{{QTI_NAMESPACE}}}qti-mapping") is None
    assert _response_processing_template(single_item) == (
        "https://purl.imsglobal.org/spec/qti/v3p0/rptemplates/map_response.xml"
    )
    multiple_processing = _response_processing(multiple_item)
    assert "template" not in multiple_processing.attrib
    multiple_condition = multiple_processing.find(
        f"{{{QTI_NAMESPACE}}}qti-response-condition/{{{QTI_NAMESPACE}}}qti-response-if"
    )
    assert multiple_condition is not None
    multiple_match = multiple_condition.find(f"{{{QTI_NAMESPACE}}}qti-match")
    assert multiple_match is not None
    multiple_variable = multiple_match.find(f"{{{QTI_NAMESPACE}}}qti-variable")
    multiple_correct = multiple_match.find(f"{{{QTI_NAMESPACE}}}qti-correct")
    assert multiple_variable is not None
    assert multiple_correct is not None
    assert multiple_variable.attrib["identifier"] == "RESPONSE"
    assert multiple_correct.attrib["identifier"] == "RESPONSE"
    assert next(iter(_choice_interaction(single_item))).tag == f"{{{QTI_NAMESPACE}}}qti-prompt"
    assert (_interaction_prompt(single_item, "qti-choice-interaction").text or "").startswith(
        "Vilket svar kopplar"
    )
    assert (_interaction_prompt(multiple_item, "qti-choice-interaction").text or "").startswith(
        "Vilka drag stärker"
    )
    assert item_body_paragraphs(single_item) == []
    assert item_body_paragraphs(multiple_item) == []


def test_gap_fill_package_encodes_text_entries_and_accepted_values(tmp_path: Path) -> None:
    sample_dir = write_sample(keyed_sample("gap-fill-text-entry"), tmp_path)
    item = _item_root(sample_dir / "qti-package.zip")
    report = read_report(sample_dir / "qti-validation-report.json")
    xml = _item_xml(sample_dir / "qti-package.zip")

    response = _response_declaration(item)
    assert response.attrib["identifier"] == "RESPONSE_gap_001"
    assert response.attrib["base-type"] == "string"
    assert response.attrib["cardinality"] == "single"
    assert item.find(f".//{{{QTI_NAMESPACE}}}qti-text-entry-interaction") is not None
    assert _correct_values(item) == ["ATP"]
    assert 'map-key="ATP"' in xml
    assert 'map-key="atp"' in xml
    assert _mapping(item).attrib == {
        "default-value": "0",
        "lower-bound": "0",
        "upper-bound": "1",
    }
    assert [
        (entry.attrib["map-key"], entry.attrib["mapped-value"], entry.attrib["case-sensitive"])
        for entry in _map_entries(item)
    ] == [("ATP", "1", "false"), ("atp", "1", "false")]
    assert item.find(f"{{{QTI_NAMESPACE}}}qti-response-processing") is None
    assert json_string(report, "target_support_status") == (
        ExamNetQtiTargetSupportStatus.PROOF_GATED
    )


def test_gap_fill_package_splits_max_score_equally_across_gaps() -> None:
    plan = build_examnet_qti_package_plan(
        package_name="gap-split",
        items=(
            ExamNetQtiItem(
                item_id="item_001",
                sequence=1,
                title="Lucktext med två luckor",
                interaction_type=ExamNetQtiInteractionType.GAP_FILL,
                prompt_lines=("Fyll i _____ och _____.",),
                max_score=3,
                text_entry_gaps=(
                    ExamNetQtiTextEntryGap(
                        response_identifier="RESPONSE_gap_001",
                        label="Lucka 1",
                        accepted_values=("alfa", "Alfa"),
                    ),
                    ExamNetQtiTextEntryGap(
                        response_identifier="RESPONSE_gap_002",
                        label="Lucka 2",
                        accepted_values=("beta",),
                    ),
                ),
            ),
        ),
    )
    zip_bytes = build_examnet_qti_zip_bytes(plan)

    with zipfile.ZipFile(BytesIO(zip_bytes)) as archive:
        item = ElementTree.fromstring(archive.read("items/item_001.xml"))

    mappings = item.findall(f".//{{{QTI_NAMESPACE}}}qti-mapping")
    assert len(mappings) == 2
    for mapping in mappings:
        assert mapping.attrib == {
            "default-value": "0",
            "lower-bound": "0",
            "upper-bound": "1.5",
        }
    assert [entry.attrib["mapped-value"] for entry in _map_entries(item)] == ["1.5", "1.5", "1.5"]


def test_export_only_matching_sample_preserves_visible_content_as_manual_free_text(
    tmp_path: Path,
) -> None:
    samples = {sample.name: sample for sample in examnet_qti_manual_unkeyed_samples()}
    sample_dir = write_sample(samples["manual-matching-preserved-as-free-text"], tmp_path)
    item = _item_root(sample_dir / "qti-package.zip")
    report = read_report(sample_dir / "qti-validation-report.json")

    assert item.find(f".//{{{QTI_NAMESPACE}}}qti-extended-text-interaction") is not None
    assert item.find(f".//{{{QTI_NAMESPACE}}}qti-correct-response") is None
    assert item.find(f".//{{{QTI_NAMESPACE}}}qti-mapping") is None
    assert item.find(f"{{{QTI_NAMESPACE}}}qti-response-processing") is None
    prompt = _interaction_prompt(item, "qti-extended-text-interaction")
    prompt_lines = [paragraph.text for paragraph in prompt.findall(f"{{{QTI_NAMESPACE}}}p")]
    assert prompt_lines[:2] == [
        "Para ihop varje begrepp med rätt förklaring.",
        "Vänster kolumn:",
    ]
    assert item_body_paragraphs(item) == []
    assert "Vänster kolumn:" in _item_xml(sample_dir / "qti-package.zip")
    assert json_string(report, "examnet_proof_status") == (
        ExamNetQtiExamNetProofStatus.VENDOR_REPORTED_UNPROVEN
    )


def test_free_text_package_uses_extended_text_without_answer_key(tmp_path: Path) -> None:
    sample_dir = write_sample(keyed_sample("free-text"), tmp_path)
    item = _item_root(sample_dir / "qti-package.zip")

    assert item.find(f".//{{{QTI_NAMESPACE}}}qti-extended-text-interaction") is not None
    assert item.find(f".//{{{QTI_NAMESPACE}}}qti-correct-response") is None
    assert _mapping(item).attrib == {
        "default-value": "0",
        "lower-bound": "0",
        "upper-bound": "9",
    }
    assert _map_entry_pairs(item) == [("CRITERION_FULL", "9")]
    assert _response_processing_template(item) == MAP_RESPONSE_TEMPLATE
    assert "Resonera kring" in (
        _interaction_prompt(item, "qti-extended-text-interaction").text or ""
    )
    assert item_body_paragraphs(item) == []


def test_matching_package_is_valid_but_examnet_proof_gated(tmp_path: Path) -> None:
    sample_dir = write_sample(keyed_sample("matching-proof-gated"), tmp_path)
    item = _item_root(sample_dir / "qti-package.zip")
    report = read_report(sample_dir / "qti-validation-report.json")

    match_interaction = item.find(f".//{{{QTI_NAMESPACE}}}qti-match-interaction")
    assert match_interaction is not None
    assert "shuffle" not in match_interaction.attrib
    assert _response_declaration(item).attrib["base-type"] == "directedPair"
    assert _correct_values(item) == [
        "left_001 right_001",
        "left_002 right_002",
        "left_003 right_003",
        "left_004 right_004",
    ]
    assert _mapping(item).attrib == {
        "default-value": "0",
        "lower-bound": "0",
        "upper-bound": "4",
    }
    assert _map_entry_pairs(item) == [
        ("left_001 right_001", "1"),
        ("left_002 right_002", "1"),
        ("left_003 right_003", "1"),
        ("left_004 right_004", "1"),
    ]
    assert _response_processing_template(item) == MAP_RESPONSE_TEMPLATE
    assert next(iter(match_interaction)).tag == f"{{{QTI_NAMESPACE}}}qti-prompt"
    assert (_interaction_prompt(item, "qti-match-interaction").text or "").startswith(
        "Para ihop varje cellstruktur"
    )
    assert item_body_paragraphs(item) == []
    assert json_string(report, "target_support_status") == (
        ExamNetQtiTargetSupportStatus.PROOF_GATED
    )
    assert json_string(report, "examnet_proof_status") == (ExamNetQtiExamNetProofStatus.NOT_PROVEN)


def _item_root(package_path: Path) -> ElementTree.Element:
    return ElementTree.fromstring(_item_xml(package_path).encode("utf-8"))


def _item_xml(package_path: Path) -> str:
    with zipfile.ZipFile(package_path) as archive:
        item_names = sorted(name for name in archive.namelist() if name.startswith("items/"))
        return archive.read(item_names[0]).decode("utf-8")


def _response_declaration(item: ElementTree.Element) -> ElementTree.Element:
    declaration = item.find(f"{{{QTI_NAMESPACE}}}qti-response-declaration")
    assert declaration is not None
    return declaration


def _choice_interaction(item: ElementTree.Element) -> ElementTree.Element:
    interaction = item.find(f".//{{{QTI_NAMESPACE}}}qti-choice-interaction")
    assert interaction is not None
    return interaction


def _interaction_prompt(item: ElementTree.Element, tag: str) -> ElementTree.Element:
    interaction = item.find(f".//{{{QTI_NAMESPACE}}}{tag}")
    assert interaction is not None
    prompt = interaction.find(f"{{{QTI_NAMESPACE}}}qti-prompt")
    assert prompt is not None
    return prompt


def _mapping(item: ElementTree.Element) -> ElementTree.Element:
    mapping = item.find(f".//{{{QTI_NAMESPACE}}}qti-mapping")
    assert mapping is not None
    return mapping


def _map_entries(item: ElementTree.Element) -> list[ElementTree.Element]:
    return item.findall(f".//{{{QTI_NAMESPACE}}}qti-map-entry")


def _map_entry_pairs(item: ElementTree.Element) -> list[tuple[str, str]]:
    return [(entry.attrib["map-key"], entry.attrib["mapped-value"]) for entry in _map_entries(item)]


def _response_processing(item: ElementTree.Element) -> ElementTree.Element:
    processing = item.find(f"{{{QTI_NAMESPACE}}}qti-response-processing")
    assert processing is not None
    return processing


def _response_processing_template(item: ElementTree.Element) -> str:
    return _response_processing(item).attrib["template"]


def _correct_values(item: ElementTree.Element) -> list[str]:
    return [
        value.text or ""
        for value in item.findall(
            f".//{{{QTI_NAMESPACE}}}qti-correct-response/{{{QTI_NAMESPACE}}}qti-value"
        )
    ]
