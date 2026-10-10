"""Zip codec for versioned exam workspace containers (Mina filer payload).

Layout: ``manifest.json`` (schema version, document identity, digests),
``document.json`` (the native exam document), ``assets/<asset_id>``.
Parsing is fail-closed: schema, digest, and identity mismatches raise
``DomainError`` rather than returning partial content.
"""

import hashlib
import io
import json
import zipfile

from pydantic import ValidationError

from skriptoteket.domain.curated_apps.exam_workspace.container import (
    EXAM_WORKSPACE_CONTAINER_SCHEMA_VERSION,
    ExamWorkspaceContainerContent,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    native_exam_document_json_bytes,
    parse_native_exam_document,
)
from skriptoteket.domain.errors import DomainError, ErrorCode

_MANIFEST_NAME = "manifest.json"
_DOCUMENT_NAME = "document.json"
_ASSET_PREFIX = "assets/"
_FIXED_ZIP_DATETIME = (1980, 1, 1, 0, 0, 0)


def _invalid(message: str) -> DomainError:
    return DomainError(code=ErrorCode.VALIDATION_ERROR, message=message)


class ExamWorkspaceContainerCodec:
    """Deterministic zip serialization for exam workspace containers."""

    def build(self, *, content: ExamWorkspaceContainerContent) -> bytes:
        document_bytes = native_exam_document_json_bytes(content.document)
        manifest = {
            "schema_version": EXAM_WORKSPACE_CONTAINER_SCHEMA_VERSION,
            "document_id": str(content.document.document_id),
            "revision": content.document.revision,
            "document_sha256": hashlib.sha256(document_bytes).hexdigest(),
            "notes": list(content.notes),
        }
        manifest_bytes = json.dumps(
            manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, payload in (
                (_MANIFEST_NAME, manifest_bytes),
                (_DOCUMENT_NAME, document_bytes),
                *(
                    (f"{_ASSET_PREFIX}{asset_id}", content.assets_by_id[asset_id])
                    for asset_id in sorted(content.assets_by_id)
                ),
            ):
                info = zipfile.ZipInfo(name, date_time=_FIXED_ZIP_DATETIME)
                archive.writestr(info, payload)
        return buffer.getvalue()

    def parse(self, *, content: bytes) -> ExamWorkspaceContainerContent:
        try:
            archive = zipfile.ZipFile(io.BytesIO(content))
        except zipfile.BadZipFile as error:
            raise _invalid("Dokumentfilen kunde inte läsas.") from error

        with archive:
            names = set(archive.namelist())
            if _MANIFEST_NAME not in names or _DOCUMENT_NAME not in names:
                raise _invalid("Dokumentfilen saknar manifest eller dokumentinnehåll.")
            try:
                manifest = json.loads(archive.read(_MANIFEST_NAME).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise _invalid("Dokumentets manifest kunde inte läsas.") from error
            if manifest.get("schema_version") != EXAM_WORKSPACE_CONTAINER_SCHEMA_VERSION:
                raise _invalid("Dokumentfilen har en okänd schemaversion.")

            document_bytes = archive.read(_DOCUMENT_NAME)
            if hashlib.sha256(document_bytes).hexdigest() != manifest.get("document_sha256"):
                raise _invalid("Dokumentinnehållet matchar inte manifestet.")
            document = parse_native_exam_document(document_bytes)
            if str(document.document_id) != manifest.get("document_id"):
                raise _invalid("Dokumentets identitet matchar inte manifestet.")
            if document.revision != manifest.get("revision"):
                raise _invalid("Dokumentets version matchar inte manifestet.")

            assets_by_id: dict[str, bytes] = {}
            for name in names - {_MANIFEST_NAME, _DOCUMENT_NAME}:
                if not name.startswith(_ASSET_PREFIX) or "/" in name[len(_ASSET_PREFIX) :]:
                    raise _invalid("Dokumentfilen innehåller en otillåten post.")
                assets_by_id[name[len(_ASSET_PREFIX) :]] = archive.read(name)

            notes_raw = manifest.get("notes", [])
            if not isinstance(notes_raw, list) or any(
                not isinstance(note, str) for note in notes_raw
            ):
                raise _invalid("Dokumentets manifest har ogiltiga anteckningar.")

            try:
                return ExamWorkspaceContainerContent(
                    document=document,
                    assets_by_id=assets_by_id,
                    notes=tuple(notes_raw),
                )
            except ValidationError as error:
                raise _invalid("Dokumentets resurser matchar inte innehållet.") from error
