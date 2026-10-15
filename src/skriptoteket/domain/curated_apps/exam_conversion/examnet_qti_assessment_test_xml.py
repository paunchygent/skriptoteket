"""QTI 3.0 qti-assessment-test serialization for Exam.net-oriented packages.

Purpose:
    Serialize the package-level `qti-assessment-test` that wires every generated
    assessment item into one linear test part, matching the empirically
    confirmed Exam.net import skeleton.

Relationships:
    - Used by `domain.examnet_qti_package` when planning package files.
    - Imports the QTI 3.0 namespace constants from `domain.examnet_qti_terms`.
"""

from __future__ import annotations

from xml.etree import ElementTree

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_terms import (
    QTI_NAMESPACE,
    QTI_SCHEMA_LOCATION,
    XSI_NAMESPACE,
)

EXAMNET_QTI_ASSESSMENT_TEST_PATH = "assessment.xml"
EXAMNET_QTI_TEST_RESOURCE_IDENTIFIER = "res_test"
EXAMNET_QTI_TEST_RESOURCE_TYPE = "imsqti_test_xmlv3p0"


def serialize_qti_assessment_test(
    *,
    title: str,
    item_ids: tuple[str, ...],
) -> bytes:
    """Serialize the package `qti-assessment-test` to UTF-8 XML bytes."""

    ElementTree.register_namespace("", QTI_NAMESPACE)
    ElementTree.register_namespace("xsi", XSI_NAMESPACE)
    root = ElementTree.Element(
        _qti("qti-assessment-test"),
        {
            _xsi("schemaLocation"): QTI_SCHEMA_LOCATION,
            "identifier": "examnet_qti_test",
            "title": title,
        },
    )
    part = ElementTree.SubElement(
        root,
        _qti("qti-test-part"),
        {
            "identifier": "part_001",
            "navigation-mode": "linear",
            "submission-mode": "individual",
        },
    )
    section = ElementTree.SubElement(
        part,
        _qti("qti-assessment-section"),
        {
            "identifier": "section_001",
            "title": title,
            "visible": "true",
        },
    )
    for item_id in item_ids:
        ElementTree.SubElement(
            section,
            _qti("qti-assessment-item-ref"),
            {
                "identifier": f"ref_{item_id}",
                "href": f"items/{item_id}.xml",
                "fixed": "false",
            },
        )
    ElementTree.indent(root, space="  ")
    xml_text = ElementTree.tostring(
        root,
        encoding="unicode",
        xml_declaration=False,
        short_empty_elements=True,
    )
    return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_text}\n'.encode("utf-8")


def _qti(local_name: str) -> str:
    return f"{{{QTI_NAMESPACE}}}{local_name}"


def _xsi(local_name: str) -> str:
    return f"{{{XSI_NAMESPACE}}}{local_name}"
