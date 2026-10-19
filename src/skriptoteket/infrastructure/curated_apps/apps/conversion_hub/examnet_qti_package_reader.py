"""Safe reader for untrusted uploaded QTI 3.0 packages (zip bytes).

Purpose:
    Open an uploaded QTI 3.0 package, refuse unsafe or malformed archives with
    Swedish validation errors, and return the item XML files in assessment-test
    order plus every package file by normalized package-relative path.

Relationships:
    Implements ``ExamNetQtiPackageReaderProtocol`` for the QTI import lane; it
    does not parse item content. The read-side value objects live in
    ``domain.examnet_qti_import_contracts`` and the export writes the same
    package layout through ``domain.examnet_qti_package``.
"""

from __future__ import annotations

import posixpath
import zipfile
import zlib
from io import BytesIO
from types import MappingProxyType
from xml.etree import ElementTree

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_assessment_test_xml import (
    EXAMNET_QTI_TEST_RESOURCE_TYPE,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_import_contracts import (
    ExamNetQtiPackageItemSource,
    ExamNetQtiPackageSource,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_manifest import (
    IMSCP_NAMESPACE,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_terms import QTI_NAMESPACE
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_untrusted_xml import (
    parse_untrusted_qti_xml,
)
from skriptoteket.domain.errors import validation_error

MAX_MEMBERS = 2000
MAX_MEMBER_BYTES = 20 * 1024 * 1024
MAX_TOTAL_BYTES = 100 * 1024 * 1024

_ITEM_RESOURCE_TYPE = "imsqti_item_xmlv3p0"
_MANIFEST_NAME = "imsmanifest.xml"
_QTI_RESOURCE_TYPE_PREFIX = "imsqti_"

_NOT_A_ZIP = "Filen är inte ett QTI-paket (zip)."
_TOO_LARGE = "QTI-paketet är för stort eller innehåller för många filer."
_ENCRYPTED = "QTI-paketet är krypterat och kan inte läsas."
_INVALID_PATH = "QTI-paketet innehåller en ogiltig sökväg."
_MISSING_MANIFEST = "QTI-paketet saknar imsmanifest.xml."
_INVALID_XML = "QTI-paketet innehåller ogiltig XML."
_DUPLICATE_ITEM_REFERENCE = "QTI-paketet hänvisar till samma fråga mer än en gång."
_UNSUPPORTED_VERSION = (
    "QTI-paketet använder en QTI-version som inte stöds. Endast QTI 3.0 kan importeras."
)
_MISSING_FILE = "QTI-paketet saknar en fil som manifestet pekar på."
_NO_ITEMS = "QTI-paketet innehåller inga frågor."


class ExamNetQtiPackageReader:
    """Open an uploaded QTI 3.0 package behind the reader protocol."""

    def read(self, *, content: bytes) -> ExamNetQtiPackageSource:
        archive = _open_archive(content)
        with archive:
            files = _read_members(archive)

        manifest_bytes = files.get(_MANIFEST_NAME)
        if manifest_bytes is None:
            raise validation_error(_MISSING_MANIFEST)
        manifest = _parse_xml(manifest_bytes, path=_MANIFEST_NAME)
        if _namespace_of(manifest.tag) != IMSCP_NAMESPACE:
            raise validation_error(_UNSUPPORTED_VERSION)

        item_paths = _item_paths_in_test_order(manifest=manifest, files=files)
        if not item_paths:
            raise validation_error(_NO_ITEMS)

        seen: set[str] = set()
        for path in item_paths:
            if path in seen:
                raise validation_error(_DUPLICATE_ITEM_REFERENCE, {"path": path})
            seen.add(path)

        items: list[ExamNetQtiPackageItemSource] = []
        for path in item_paths:
            payload = files.get(path)
            if payload is None:
                raise validation_error(_MISSING_FILE, {"path": path})
            items.append(ExamNetQtiPackageItemSource(path=path, xml=payload))
        return ExamNetQtiPackageSource(items=tuple(items), files=MappingProxyType(files))


def _open_archive(content: bytes) -> zipfile.ZipFile:
    try:
        return zipfile.ZipFile(BytesIO(content))
    except (zipfile.BadZipFile, zipfile.LargeZipFile, ValueError, OSError) as error:
        raise validation_error(_NOT_A_ZIP) from error


def _read_members(archive: zipfile.ZipFile) -> dict[str, bytes]:
    infos = [info for info in archive.infolist() if not info.filename.endswith("/")]
    if len(infos) > MAX_MEMBERS:
        raise validation_error(_TOO_LARGE)

    total_bytes = 0
    for info in infos:
        if info.flag_bits & 0x1:
            raise validation_error(_ENCRYPTED)
        if info.file_size > MAX_MEMBER_BYTES:
            raise validation_error(_TOO_LARGE)
        total_bytes += info.file_size
        if total_bytes > MAX_TOTAL_BYTES:
            raise validation_error(_TOO_LARGE)

    files: dict[str, bytes] = {}
    for info in infos:
        name = _normalized_member_name(info.filename)
        payload = _read_member(archive, info)
        if len(payload) != info.file_size:
            raise validation_error(_TOO_LARGE)
        files[name] = payload
    return files


def _read_member(archive: zipfile.ZipFile, info: zipfile.ZipInfo) -> bytes:
    try:
        return archive.read(info)
    except (
        zipfile.BadZipFile,
        zlib.error,
        RuntimeError,
        NotImplementedError,
        ValueError,
    ) as error:
        raise validation_error(_NOT_A_ZIP) from error


def _normalized_member_name(raw_name: str) -> str:
    if raw_name.startswith("/") or "\\" in raw_name:
        raise validation_error(_INVALID_PATH)
    normalized = posixpath.normpath(raw_name)
    if normalized == ".." or normalized.startswith("../"):
        raise validation_error(_INVALID_PATH)
    return normalized


def _parse_xml(payload: bytes, *, path: str) -> ElementTree.Element:
    return parse_untrusted_qti_xml(payload, path=path, invalid_message=_INVALID_XML)


def _item_paths_in_test_order(
    *, manifest: ElementTree.Element, files: dict[str, bytes]
) -> list[str]:
    resources = manifest.findall(f".//{{{IMSCP_NAMESPACE}}}resource")
    for resource in resources:
        resource_type = resource.get("type", "")
        if resource_type.startswith(_QTI_RESOURCE_TYPE_PREFIX) and resource_type not in (
            _ITEM_RESOURCE_TYPE,
            EXAMNET_QTI_TEST_RESOURCE_TYPE,
        ):
            raise validation_error(_UNSUPPORTED_VERSION)

    test_resource = next(
        (
            resource
            for resource in resources
            if resource.get("type") == EXAMNET_QTI_TEST_RESOURCE_TYPE
        ),
        None,
    )
    if test_resource is not None:
        return _test_referenced_item_paths(test_resource=test_resource, files=files)

    paths: list[str] = []
    for resource in resources:
        if resource.get("type") != _ITEM_RESOURCE_TYPE:
            continue
        paths.append(_resolve_path(base_dir="", href=_required_href(resource)))
    return paths


def _test_referenced_item_paths(
    *, test_resource: ElementTree.Element, files: dict[str, bytes]
) -> list[str]:
    test_path = _resolve_path(base_dir="", href=_required_href(test_resource))
    test_bytes = files.get(test_path)
    if test_bytes is None:
        raise validation_error(_MISSING_FILE, {"path": test_path})

    test_root = _parse_xml(test_bytes, path=test_path)
    if _namespace_of(test_root.tag) != QTI_NAMESPACE:
        raise validation_error(_UNSUPPORTED_VERSION)

    base_dir = posixpath.dirname(test_path)
    paths: list[str] = []
    for ref in test_root.iter(f"{{{QTI_NAMESPACE}}}qti-assessment-item-ref"):
        paths.append(_resolve_path(base_dir=base_dir, href=_required_href(ref)))
    return paths


def _required_href(element: ElementTree.Element) -> str:
    href = element.get("href")
    if href is None:
        raise validation_error(_MISSING_FILE, {"path": ""})
    return href


def _resolve_path(*, base_dir: str, href: str) -> str:
    if not href or href.startswith("/") or "\\" in href:
        raise validation_error(_INVALID_PATH)
    resolved = posixpath.normpath(posixpath.join(base_dir, href))
    if resolved == ".." or resolved.startswith("../"):
        raise validation_error(_INVALID_PATH)
    return resolved


def _namespace_of(tag: str) -> str | None:
    if tag.startswith("{"):
        return tag[1:].split("}", 1)[0]
    return None
