"""Shared builders for the ExamNet QTI package reader tests.

Purpose:
    Hold the zip builders, manifest/item XML builders, Swedish refusal
    message constants, and the shared reader/writer instances used by the
    QTI package reader test modules in this directory.

Relationships:
    Used by ``test_examnet_qti_package_reader`` (package, version and
    order semantics) and
    ``test_examnet_qti_package_reader_archive_safety`` (untrusted
    archive and XML refusals).
"""

from __future__ import annotations

import dataclasses
import io
import zipfile
from pathlib import Path

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_manifest import (
    IMSCP_NAMESPACE,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_package import (
    build_examnet_qti_package_plan,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_terms import QTI_NAMESPACE
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub import examnet_qti_package_reader
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_qti_writer import (
    ExamNetQtiPackageWriter,
)
from tests.unit.domain.curated_apps.exam_conversion.examnet_qti_test_support import (
    keyed_sample,
)

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
