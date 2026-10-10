"""IMS content-packaging manifest serialization for Exam.net QTI packages.

Purpose:
    Serialize the `imsmanifest.xml` that lists every item resource, its image
    files and the assessmentTest resource with its item dependencies.

Relationships:
    - Used by `domain.examnet_qti_package` when planning package files.
    - Validated by `domain.examnet_qti_validation` against the same IMS CP namespace.
    - Shares the XSI namespace constant with `domain.examnet_qti_xml`.
"""

from __future__ import annotations

from xml.etree import ElementTree

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_assessment_test_xml import (
    EXAMNET_QTI_ASSESSMENT_TEST_PATH,
    EXAMNET_QTI_TEST_RESOURCE_IDENTIFIER,
    EXAMNET_QTI_TEST_RESOURCE_TYPE,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiPackageFile,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_xml import XSI_NAMESPACE

IMSCP_NAMESPACE = "http://www.imsglobal.org/xsd/imscp_v1p1"
IMSCP_SCHEMA_LOCATION = (
    "http://www.imsglobal.org/xsd/imscp_v1p1 http://www.imsglobal.org/xsd/imscp_v1p1.xsd"
)


def serialize_qti_manifest(
    *,
    item_files: tuple[ExamNetQtiPackageFile, ...],
    image_files_by_item_id: dict[str, tuple[ExamNetQtiPackageFile, ...]],
) -> bytes:
    ElementTree.register_namespace("", IMSCP_NAMESPACE)
    ElementTree.register_namespace("xsi", XSI_NAMESPACE)
    manifest = ElementTree.Element(
        _cp("manifest"),
        {
            "identifier": "examnet_qti_package",
            _xsi("schemaLocation"): IMSCP_SCHEMA_LOCATION,
        },
    )
    metadata = ElementTree.SubElement(manifest, _cp("metadata"))
    schema = ElementTree.SubElement(metadata, _cp("schema"))
    schema.text = "QTIv2.1 Package"
    schema_version = ElementTree.SubElement(metadata, _cp("schemaversion"))
    schema_version.text = "1.0.0"
    ElementTree.SubElement(manifest, _cp("organizations"))
    resources = ElementTree.SubElement(manifest, _cp("resources"))
    for item_file in item_files:
        item_id = item_file.relative_path.removeprefix("items/").removesuffix(".xml")
        resource = ElementTree.SubElement(
            resources,
            _cp("resource"),
            {
                "identifier": f"res_{item_id}",
                "type": "imsqti_item_xmlv2p1",
                "href": item_file.relative_path,
            },
        )
        ElementTree.SubElement(resource, _cp("file"), {"href": item_file.relative_path})
        for image_file in image_files_by_item_id[item_id]:
            ElementTree.SubElement(resource, _cp("file"), {"href": image_file.relative_path})
    test_resource = ElementTree.SubElement(
        resources,
        _cp("resource"),
        {
            "identifier": EXAMNET_QTI_TEST_RESOURCE_IDENTIFIER,
            "type": EXAMNET_QTI_TEST_RESOURCE_TYPE,
            "href": EXAMNET_QTI_ASSESSMENT_TEST_PATH,
        },
    )
    ElementTree.SubElement(test_resource, _cp("file"), {"href": EXAMNET_QTI_ASSESSMENT_TEST_PATH})
    for item_file in item_files:
        item_id = item_file.relative_path.removeprefix("items/").removesuffix(".xml")
        ElementTree.SubElement(
            test_resource, _cp("dependency"), {"identifierref": f"res_{item_id}"}
        )
    ElementTree.indent(manifest, space="  ")
    xml_text = ElementTree.tostring(
        manifest,
        encoding="unicode",
        xml_declaration=False,
        short_empty_elements=True,
    )
    return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_text}\n'.encode("utf-8")


def _cp(local_name: str) -> str:
    return f"{{{IMSCP_NAMESPACE}}}{local_name}"


def _xsi(local_name: str) -> str:
    return f"{{{XSI_NAMESPACE}}}{local_name}"
