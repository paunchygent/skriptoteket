"""Adversarial tests for untrusted QTI archives and XML.

Purpose:
    Prove the zip reader refuses unsafe or malformed archives with the
    exact Swedish validation messages: non-zip bytes, encrypted members,
    missing manifests, invalid paths, member/size limits, doctype and
    entity constructions, malformed or mistyped XML.

Relationships:
    Exercises ``ExamNetQtiPackageReader`` with synthetic zips built by
    ``examnet_qti_package_reader_test_support``. Package, version and
    order semantics live in ``test_examnet_qti_package_reader``.
"""

from __future__ import annotations

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_manifest import (
    IMSCP_NAMESPACE,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub import examnet_qti_package_reader
from tests.unit.infrastructure.curated_apps.apps.conversion_hub.examnet_qti_package_reader_test_support import (  # noqa: E501
    _ENCRYPTED,
    _INVALID_PATH,
    _INVALID_XML,
    _MISSING_MANIFEST,
    _NO_ITEMS,
    _NOT_A_ZIP,
    _READER,
    _TOO_LARGE,
    _UNSAFE_XML,
    _assessment_xml,
    _encrypted_member_zip,
    _item_xml,
    _manifest_xml,
    _test_resource,
    _utf16_with_entity,
    _zip_bytes,
)

pytestmark = pytest.mark.unit


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
