"""Adversarial tests for the QTI 3.0 package, version and order semantics.

Purpose:
    Prove the zip reader returns item XML in assessment-test order with
    every package file present, and that it refuses unsupported QTI
    versions, missing files, empty item sets and duplicate references
    with the exact Swedish validation messages.

Relationships:
    Exercises ``ExamNetQtiPackageReader`` against the real
    ``tests/fixtures/exam_conversion/reference-qti-package.zip`` export
    and packages built with the export writer. Untrusted archive and XML
    refusals live in
    ``test_examnet_qti_package_reader_archive_safety``; shared builders
    live in ``examnet_qti_package_reader_test_support``.
"""

from __future__ import annotations

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_terms import QTI_NAMESPACE
from skriptoteket.domain.errors import DomainError, ErrorCode
from tests.unit.infrastructure.curated_apps.apps.conversion_hub.examnet_qti_package_reader_test_support import (  # noqa: E501
    _DUPLICATE_REFERENCE,
    _MISSING_FILE,
    _NO_ITEMS,
    _READER,
    _REFERENCE_PACKAGE,
    _UNSUPPORTED_VERSION,
    _assessment_xml,
    _item_resource,
    _item_xml,
    _manifest_xml,
    _members,
    _test_resource,
    _two_item_package_bytes,
    _zip_bytes,
)

pytestmark = pytest.mark.unit


def test_reference_package_returns_test_order_and_every_file() -> None:
    content = _REFERENCE_PACKAGE.read_bytes()

    source = _READER.read(content=content)

    assert [item.path for item in source.items] == [
        "items/item_001.xml",
        "items/item_002.xml",
        "items/item_003.xml",
        "items/item_004.xml",
        "items/item_005.xml",
        "items/item_006.xml",
        "items/item_007.xml",
    ]
    assert dict(source.files) == _members(content)
    assert all(source.files[item.path] == item.xml for item in source.items)


def test_test_order_wins_over_zip_member_order() -> None:
    members = _members(_two_item_package_bytes())
    assert members["items/item_001.xml"] != members["items/item_002.xml"]
    reordered = _zip_bytes(
        [
            ("imsmanifest.xml", members["imsmanifest.xml"]),
            ("assessment.xml", members["assessment.xml"]),
            ("items/item_002.xml", members["items/item_002.xml"]),
            ("items/item_001.xml", members["items/item_001.xml"]),
        ]
    )

    source = _READER.read(content=reordered)

    assert [item.path for item in source.items] == ["items/item_001.xml", "items/item_002.xml"]


def test_manifest_without_test_resource_uses_item_resources_in_manifest_order() -> None:
    manifest = _manifest_xml(
        _item_resource(identifier="res_item_002", href="items/item_002.xml"),
        _item_resource(identifier="res_item_001", href="items/item_001.xml"),
    )
    content = _zip_bytes(
        [
            ("imsmanifest.xml", manifest),
            ("items/item_001.xml", _item_xml("item_001")),
            ("items/item_002.xml", _item_xml("item_002")),
        ]
    )

    source = _READER.read(content=content)

    assert [item.path for item in source.items] == ["items/item_002.xml", "items/item_001.xml"]


def test_manifest_without_namespace_is_refused_with_version_message() -> None:
    manifest = b'<?xml version="1.0"?><manifest />'

    with pytest.raises(DomainError) as refusal:
        _READER.read(content=_zip_bytes([("imsmanifest.xml", manifest)]))

    assert refusal.value.message == _UNSUPPORTED_VERSION


def test_qti_2_1_manifest_is_refused() -> None:
    manifest = _manifest_xml(
        _item_resource(
            identifier="res_item_001",
            href="items/item_001.xml",
            resource_type="imsqti_item_xmlv2p1",
        ),
        _test_resource(href="assessment.xml", resource_type="imsqti_test_xmlv2p1"),
    )
    content = _zip_bytes(
        [
            ("imsmanifest.xml", manifest),
            ("assessment.xml", _assessment_xml("items/item_001.xml")),
            ("items/item_001.xml", _item_xml("item_001")),
        ]
    )

    with pytest.raises(DomainError) as refusal:
        _READER.read(content=content)

    assert refusal.value.message == _UNSUPPORTED_VERSION


def test_qti_2_1_package_namespace_is_refused_with_version_message() -> None:
    manifest = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<manifest xmlns="http://www.imsglobal.org/xsd/imscp_v1p1" identifier="m1">'
        '<resources><resource identifier="i1" type="imsqti_item_xmlv2p1"'
        ' href="item1.xml"><file href="item1.xml" /></resource></resources>'
        "</manifest>"
    ).encode("utf-8")
    item = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<assessmentItem xmlns="http://www.imsglobal.org/xsd/imsqti_v2p1"'
        ' identifier="i1" title="Fråga" adaptive="false" timeDependent="false" />'
    ).encode("utf-8")
    content = _zip_bytes([("imsmanifest.xml", manifest), ("item1.xml", item)])

    with pytest.raises(DomainError) as refusal:
        _READER.read(content=content)

    assert refusal.value.message == _UNSUPPORTED_VERSION


def test_qti_2_1_assessment_test_namespace_is_refused() -> None:
    manifest = _manifest_xml(_test_resource(href="assessment.xml"))
    content = _zip_bytes(
        [
            ("imsmanifest.xml", manifest),
            (
                "assessment.xml",
                _assessment_xml(
                    "items/item_001.xml",
                    namespace="http://www.imsglobal.org/xsd/imsqti_v2p1",
                ),
            ),
        ]
    )

    with pytest.raises(DomainError) as refusal:
        _READER.read(content=content)

    assert refusal.value.message == _UNSUPPORTED_VERSION


def test_test_referencing_missing_item_is_refused() -> None:
    manifest = _manifest_xml(
        _item_resource(identifier="res_item_001", href="items/item_001.xml"),
        _test_resource(href="assessment.xml"),
    )
    content = _zip_bytes(
        [
            ("imsmanifest.xml", manifest),
            ("assessment.xml", _assessment_xml("items/item_001.xml")),
        ]
    )

    with pytest.raises(DomainError) as refusal:
        _READER.read(content=content)

    assert refusal.value.message == _MISSING_FILE
    assert refusal.value.details == {"path": "items/item_001.xml"}


def test_test_without_item_refs_is_refused() -> None:
    manifest = _manifest_xml(_test_resource(href="assessment.xml"))
    content = _zip_bytes(
        [
            ("imsmanifest.xml", manifest),
            ("assessment.xml", _assessment_xml()),
        ]
    )

    with pytest.raises(DomainError) as refusal:
        _READER.read(content=content)

    assert refusal.value.message == _NO_ITEMS


def test_assessment_referencing_the_same_item_twice_is_refused() -> None:
    manifest = _manifest_xml(_test_resource(href="assessment.xml"))
    content = _zip_bytes(
        [
            ("imsmanifest.xml", manifest),
            (
                "assessment.xml",
                _assessment_xml("items/item_001.xml", "items/item_001.xml"),
            ),
            ("items/item_001.xml", _item_xml("item_001")),
        ]
    )

    with pytest.raises(DomainError) as refusal:
        _READER.read(content=content)

    assert refusal.value.code is ErrorCode.VALIDATION_ERROR
    assert refusal.value.message == _DUPLICATE_REFERENCE
    assert refusal.value.details == {"path": "items/item_001.xml"}


def test_repeated_references_are_refused_before_any_item_is_parsed() -> None:
    refs = "".join(
        '<qti-assessment-item-ref identifier="ref_' + str(index) + '" href="items/item_001.xml"/>'
        for index in range(2001)
    )
    assessment = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<qti-assessment-test xmlns="{QTI_NAMESPACE}">{refs}</qti-assessment-test>'
    ).encode("utf-8")
    manifest = _manifest_xml(_test_resource(href="assessment.xml"))
    content = _zip_bytes(
        [
            ("imsmanifest.xml", manifest),
            ("assessment.xml", assessment),
        ]
    )

    with pytest.raises(DomainError) as refusal:
        _READER.read(content=content)

    assert refusal.value.code is ErrorCode.VALIDATION_ERROR
    assert refusal.value.message == _DUPLICATE_REFERENCE
    assert refusal.value.details == {"path": "items/item_001.xml"}
