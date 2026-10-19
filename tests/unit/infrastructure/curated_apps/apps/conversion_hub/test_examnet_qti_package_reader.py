"""Adversarial tests for the untrusted QTI 3.0 package reader.

Purpose:
    Prove the zip reader returns item XML in assessment-test order with every
    package file present, and that it refuses unsafe or malformed archives with
    the exact Swedish validation messages.

Relationships:
    Exercises ``ExamNetQtiPackageReader`` against the real
    ``tests/fixtures/exam_conversion/reference-qti-package.zip`` export and
    packages built with the export writer.
"""

from __future__ import annotations

import dataclasses
import io
import zipfile
from pathlib import Path

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_manifest import (
    IMSCP_NAMESPACE,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_package import (
    build_examnet_qti_package_plan,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_terms import QTI_NAMESPACE
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub import examnet_qti_package_reader
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_qti_writer import (
    ExamNetQtiPackageWriter,
)
from tests.unit.domain.curated_apps.exam_conversion.examnet_qti_test_support import (
    keyed_sample,
)

pytestmark = pytest.mark.unit

_REFERENCE_PACKAGE = Path("tests/fixtures/exam_conversion/reference-qti-package.zip")
_READER = examnet_qti_package_reader.ExamNetQtiPackageReader()
_WRITER = ExamNetQtiPackageWriter()

_NOT_A_ZIP = "Filen är inte ett QTI-paket (zip)."
_TOO_LARGE = "QTI-paketet är för stort eller innehåller för många filer."
_ENCRYPTED = "QTI-paketet är krypterat och kan inte läsas."
_INVALID_PATH = "QTI-paketet innehåller en ogiltig sökväg."
_MISSING_MANIFEST = "QTI-paketet saknar imsmanifest.xml."
_UNSAFE_XML = "QTI-paketet innehåller en otillåten XML-konstruktion."
_INVALID_XML = "QTI-paketet innehåller ogiltig XML."
_UNSUPPORTED_VERSION = (
    "QTI-paketet använder en QTI-version som inte stöds. Endast QTI 3.0 kan importeras."
)
_MISSING_FILE = "QTI-paketet saknar en fil som manifestet pekar på."
_NO_ITEMS = "QTI-paketet innehåller inga frågor."
_DUPLICATE_REFERENCE = "QTI-paketet hänvisar till samma fråga mer än en gång."


def _zip_bytes(entries: list[tuple[str, bytes]]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, payload in entries:
            archive.writestr(name, payload)
    return buffer.getvalue()


def _members(content: bytes) -> dict[str, bytes]:
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


def _encrypted_member_zip(name: str, payload: bytes) -> bytes:
    content = bytearray(_zip_bytes([(name, payload)]))
    for signature, offset in ((b"PK\x03\x04", 6), (b"PK\x01\x02", 8)):
        index = content.index(signature)
        flags = int.from_bytes(content[index + offset : index + offset + 2], "little")
        content[index + offset : index + offset + 2] = (flags | 0x1).to_bytes(2, "little")
    return bytes(content)


def _manifest_xml(*resources: str) -> bytes:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<manifest xmlns="{IMSCP_NAMESPACE}" identifier="pkg">'
        f"<resources>{''.join(resources)}</resources>"
        "</manifest>"
    ).encode("utf-8")


def _item_resource(
    *, identifier: str, href: str, resource_type: str = "imsqti_item_xmlv3p0"
) -> str:
    return f'<resource identifier="{identifier}" type="{resource_type}" href="{href}" />'


def _test_resource(*, href: str, resource_type: str = "imsqti_test_xmlv3p0") -> str:
    return f'<resource identifier="res_test" type="{resource_type}" href="{href}" />'


def _assessment_xml(*hrefs: str, namespace: str = QTI_NAMESPACE) -> bytes:
    refs = "".join(
        f'<qti-assessment-item-ref identifier="ref_{index}" href="{href}" />'
        for index, href in enumerate(hrefs)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<qti-assessment-test xmlns="{namespace}" identifier="test">{refs}'
        "</qti-assessment-test>"
    ).encode("utf-8")


def _item_xml(item_id: str) -> bytes:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<qti-assessment-item xmlns="{QTI_NAMESPACE}" identifier="{item_id}" />'
    ).encode("utf-8")


def _utf16_with_entity(xml: bytes, *, root_name: str) -> bytes:
    text = xml.decode("utf-8").split("?>", 1)[1]
    dtd = f'<!DOCTYPE {root_name} [<!ENTITY a "ENTITY_EXPANDED"><!ENTITY b "' + "&a;" * 100 + '">]>'
    return ('<?xml version="1.0" encoding="UTF-16"?>' + dtd + text).encode("utf-16")


def _two_item_package_bytes() -> bytes:
    first = keyed_sample("single-choice-mcq").items[0]
    second = dataclasses.replace(first, item_id="item_002", sequence=2)
    plan = build_examnet_qti_package_plan(
        package_name="order-package", assessment_title="Ordning", items=(first, second)
    )
    return _WRITER.build_package_bytes(plan)


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


def test_not_a_zip_is_refused() -> None:
    with pytest.raises(DomainError) as refusal:
        _READER.read(content=b"detta ar inte en zip")

    assert refusal.value.code is ErrorCode.VALIDATION_ERROR
    assert refusal.value.message == _NOT_A_ZIP


def test_encrypted_member_is_refused() -> None:
    content = _encrypted_member_zip("imsmanifest.xml", b"<manifest />")

    with pytest.raises(DomainError) as refusal:
        _READER.read(content=content)

    assert refusal.value.message == _ENCRYPTED


def test_empty_zip_is_refused() -> None:
    with pytest.raises(DomainError) as refusal:
        _READER.read(content=_zip_bytes([]))

    assert refusal.value.message == _MISSING_MANIFEST


def test_package_without_manifest_is_refused() -> None:
    content = _zip_bytes([("assessment.xml", _assessment_xml())])

    with pytest.raises(DomainError) as refusal:
        _READER.read(content=content)

    assert refusal.value.message == _MISSING_MANIFEST


def test_doctype_in_manifest_is_refused() -> None:
    manifest = b'<?xml version="1.0"?><!DOCTYPE manifest [<!ENTITY x "y">]><manifest />'

    with pytest.raises(DomainError) as refusal:
        _READER.read(content=_zip_bytes([("imsmanifest.xml", manifest)]))

    assert refusal.value.message == _UNSAFE_XML


def test_entity_like_text_in_a_comment_is_not_unsafe() -> None:
    manifest = (
        f'<?xml version="1.0"?><!-- <!ENTITY x "y"> --><manifest xmlns="{IMSCP_NAMESPACE}" />'
    ).encode("utf-8")

    with pytest.raises(DomainError) as refusal:
        _READER.read(content=_zip_bytes([("imsmanifest.xml", manifest)]))

    assert refusal.value.message != _UNSAFE_XML
    assert refusal.value.message == _NO_ITEMS


def test_manifest_without_namespace_is_refused_with_version_message() -> None:
    manifest = b'<?xml version="1.0"?><manifest />'

    with pytest.raises(DomainError) as refusal:
        _READER.read(content=_zip_bytes([("imsmanifest.xml", manifest)]))

    assert refusal.value.message == _UNSUPPORTED_VERSION


def test_malformed_manifest_xml_is_refused() -> None:
    with pytest.raises(DomainError) as refusal:
        _READER.read(content=_zip_bytes([("imsmanifest.xml", b"<manifest>")]))

    assert refusal.value.message == _INVALID_XML


def test_parent_traversal_member_is_refused() -> None:
    content = _zip_bytes([("imsmanifest.xml", b"<manifest />"), ("../evil.xml", b"evil")])

    with pytest.raises(DomainError) as refusal:
        _READER.read(content=content)

    assert refusal.value.message == _INVALID_PATH


def test_absolute_member_path_is_refused() -> None:
    content = _zip_bytes([("imsmanifest.xml", b"<manifest />"), ("/evil.xml", b"evil")])

    with pytest.raises(DomainError) as refusal:
        _READER.read(content=content)

    assert refusal.value.message == _INVALID_PATH


def test_too_many_members_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(examnet_qti_package_reader, "MAX_MEMBERS", 2)
    content = _zip_bytes([(f"file_{index}.bin", b"x") for index in range(3)])

    with pytest.raises(DomainError) as refusal:
        _READER.read(content=content)

    assert refusal.value.message == _TOO_LARGE


def test_oversized_member_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(examnet_qti_package_reader, "MAX_MEMBER_BYTES", 4)
    content = _zip_bytes([("imsmanifest.xml", b"<manifest />")])

    with pytest.raises(DomainError) as refusal:
        _READER.read(content=content)

    assert refusal.value.message == _TOO_LARGE


def test_total_size_over_limit_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(examnet_qti_package_reader, "MAX_TOTAL_BYTES", 5)
    content = _zip_bytes([("a.bin", b"1234"), ("b.bin", b"5678")])

    with pytest.raises(DomainError) as refusal:
        _READER.read(content=content)

    assert refusal.value.message == _TOO_LARGE


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


def test_utf16_manifest_with_internal_entity_is_refused() -> None:
    manifest = _manifest_xml(_test_resource(href="assessment.xml"))
    manifest = _utf16_with_entity(manifest, root_name="manifest")
    content = _zip_bytes(
        [
            ("imsmanifest.xml", manifest),
            ("assessment.xml", _assessment_xml("items/item_001.xml")),
            ("items/item_001.xml", _item_xml("item_001")),
        ]
    )

    with pytest.raises(DomainError) as refusal:
        _READER.read(content=content)

    assert refusal.value.code is ErrorCode.VALIDATION_ERROR
    assert refusal.value.message == _UNSAFE_XML


def test_utf16_manifest_with_doctype_only_is_refused() -> None:
    text = _manifest_xml(_test_resource(href="assessment.xml")).decode("utf-8").split("?>", 1)[1]
    manifest = ('<?xml version="1.0" encoding="UTF-16"?><!DOCTYPE manifest>' + text).encode(
        "utf-16"
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

    assert refusal.value.message == _UNSAFE_XML


def test_utf16_assessment_with_internal_entity_is_refused() -> None:
    manifest = _manifest_xml(_test_resource(href="assessment.xml"))
    assessment = _utf16_with_entity(
        _assessment_xml("items/item_001.xml"), root_name="qti-assessment-test"
    )
    content = _zip_bytes(
        [
            ("imsmanifest.xml", manifest),
            ("assessment.xml", assessment),
            ("items/item_001.xml", _item_xml("item_001")),
        ]
    )

    with pytest.raises(DomainError) as refusal:
        _READER.read(content=content)

    assert refusal.value.code is ErrorCode.VALIDATION_ERROR
    assert refusal.value.message == _UNSAFE_XML


def test_manifest_with_unknown_encoding_is_a_typed_refusal() -> None:
    manifest = _manifest_xml(_test_resource(href="assessment.xml")).replace(
        b'encoding="UTF-8"', b'encoding="x-does-not-exist"'
    )

    with pytest.raises(DomainError) as refusal:
        _READER.read(content=_zip_bytes([("imsmanifest.xml", manifest)]))

    assert refusal.value.code is ErrorCode.VALIDATION_ERROR
    assert refusal.value.message == _INVALID_XML


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
