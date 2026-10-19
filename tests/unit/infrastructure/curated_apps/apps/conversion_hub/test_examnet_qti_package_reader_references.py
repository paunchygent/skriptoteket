"""Adversarial tests for manifest-only duplicate item references.

Purpose:
    Prove the package reader refuses a repeated item path for every item
    path source (not only assessment-test references), before any item
    source is materialized.

Relationships:
    Exercises ``ExamNetQtiPackageReader`` with manifests that list no
    assessment test, complementing the assessment-reference duplicate
    tests in ``test_examnet_qti_package_reader``.
"""

from __future__ import annotations

import io
import zipfile

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_manifest import (
    IMSCP_NAMESPACE,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub import (
    examnet_qti_package_reader as _reader_module,
)

pytestmark = pytest.mark.unit

_READER = _reader_module.ExamNetQtiPackageReader()

_DUPLICATE_REFERENCE = "QTI-paketet hänvisar till samma fråga mer än en gång."


def _zip_bytes(entries: list[tuple[str, bytes]]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, payload in entries:
            archive.writestr(name, payload)
    return buffer.getvalue()


def _manifest_xml(*resources: str) -> bytes:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<manifest xmlns="{IMSCP_NAMESPACE}" identifier="pkg">'
        f"<resources>{''.join(resources)}</resources>"
        "</manifest>"
    ).encode("utf-8")


def _item_resource(*, identifier: str, href: str) -> str:
    return f'<resource identifier="{identifier}" type="imsqti_item_xmlv3p0" href="{href}" />'


def _item_xml(item_id: str) -> bytes:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<qti-assessment-item xmlns="http://www.imsglobal.org/xsd/imsqti_v3p0"'
        f' identifier="{item_id}" />'
    ).encode("utf-8")


def test_manifest_without_test_repeating_one_href_is_refused() -> None:
    manifest = _manifest_xml(
        _item_resource(identifier="res_item_001", href="items/item_001.xml"),
        _item_resource(identifier="res_item_002", href="items/item_001.xml"),
    )
    content = _zip_bytes(
        [
            ("imsmanifest.xml", manifest),
            ("items/item_001.xml", _item_xml("item_001")),
        ]
    )

    with pytest.raises(DomainError) as refusal:
        _READER.read(content=content)

    assert refusal.value.code is ErrorCode.VALIDATION_ERROR
    assert refusal.value.message == _DUPLICATE_REFERENCE
    assert refusal.value.details == {"path": "items/item_001.xml"}


def test_manifest_without_test_2001_repeated_refs_are_refused() -> None:
    resources = "".join(
        _item_resource(identifier=f"item_res_{index}", href="items/item_001.xml")
        for index in range(2001)
    )
    content = _zip_bytes(
        [
            ("imsmanifest.xml", _manifest_xml(resources)),
            ("items/item_001.xml", _item_xml("item_001")),
        ]
    )

    with pytest.raises(DomainError) as refusal:
        _READER.read(content=content)

    assert refusal.value.code is ErrorCode.VALIDATION_ERROR
    assert refusal.value.message == _DUPLICATE_REFERENCE
    assert refusal.value.details == {"path": "items/item_001.xml"}


def test_manifest_without_test_normalized_duplicate_href_is_refused() -> None:
    manifest = _manifest_xml(
        _item_resource(identifier="res_item_001", href="items/item_001.xml"),
        _item_resource(identifier="res_item_002", href="items/../items/item_001.xml"),
    )
    content = _zip_bytes(
        [
            ("imsmanifest.xml", manifest),
            ("items/item_001.xml", _item_xml("item_001")),
        ]
    )

    with pytest.raises(DomainError) as refusal:
        _READER.read(content=content)

    assert refusal.value.code is ErrorCode.VALIDATION_ERROR
    assert refusal.value.message == _DUPLICATE_REFERENCE
    assert refusal.value.details == {"path": "items/item_001.xml"}
