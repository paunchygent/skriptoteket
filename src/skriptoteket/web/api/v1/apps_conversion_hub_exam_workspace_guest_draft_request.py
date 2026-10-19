"""Parse the signed-in guest-draft handoff multipart request (P5).

Purpose:
    Read the one ``draft_id`` idempotency key, the ``document`` JSON, the
    ``notes`` JSON and every ``asset:<id>`` picture part of a guest handoff
    post under the vault size cap. The notes validate as the container's own
    notes type before the handler claims and creates anything.

Relationships:
    - Consumed by the exam workspace guest-drafts route in
      ``apps_conversion_hub_exam_workspace``; picture-part mismatch errors
      come from ``handlers.public_exam_workspace_exports``.
"""

from __future__ import annotations

import json
from uuid import UUID

from fastapi import Request
from pydantic import TypeAdapter, ValidationError
from starlette.datastructures import UploadFile as StarletteUploadFile

from skriptoteket.application.curated_apps.handlers.public_exam_workspace_exports import (
    asset_mismatch_error,
)
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document_json import (
    parse_native_exam_document,
)
from skriptoteket.domain.errors import DomainError, ErrorCode, validation_error

_DOCUMENT_FIELD = "document"
_DRAFT_ID_FIELD = "draft_id"
_NOTES_FIELD = "notes"
_ASSET_FIELD_PREFIX = "asset:"

_NOTES_ADAPTER = TypeAdapter(list[str])


async def read_guest_draft_request(
    *, request: Request, settings: Settings
) -> tuple[UUID, NativeExamDocument, dict[str, bytes], tuple[str, ...]]:
    """Parse the draft id, the document and notes JSON and every ``asset:<id>`` file part."""

    form = await request.form()
    draft_id_values: list[str] = []
    document_values: list[str] = []
    notes_values: list[str] = []
    uploaded_parts: list[tuple[str, bytes]] = []
    unknown_fields: list[str] = []
    total_bytes = 0

    for field_name, value in form.multi_items():
        if isinstance(value, StarletteUploadFile):
            content = await value.read()
            total_bytes += len(content)
            uploaded_parts.append((field_name, content))
            continue
        encoded = value.encode("utf-8")
        total_bytes += len(encoded)
        if field_name == _DRAFT_ID_FIELD:
            draft_id_values.append(value)
        elif field_name == _DOCUMENT_FIELD:
            document_values.append(value)
        elif field_name == _NOTES_FIELD:
            notes_values.append(value)
        else:
            unknown_fields.append(field_name)

    if total_bytes > settings.VAULT_MAX_FILE_BYTES:
        raise DomainError(
            code=ErrorCode.PAYLOAD_TOO_LARGE,
            message="Förfrågan är för stor.",
            details={
                "reason": "payload_too_large",
                "max_bytes": settings.VAULT_MAX_FILE_BYTES,
            },
        )
    if unknown_fields:
        raise validation_error(
            "Förfrågan innehåller ett okänt fält.",
            details={"reason": "unknown_field", "field": unknown_fields[0]},
        )
    if len(draft_id_values) != 1:
        raise validation_error(
            "Förfrågan måste innehålla exakt ett utkast-id.",
            details={"reason": "missing_draft_id"},
        )
    if len(document_values) != 1:
        raise validation_error(
            "Förfrågan måste innehålla exakt ett prov.",
            details={"reason": "missing_document"},
        )
    if len(notes_values) != 1:
        raise validation_error(
            "Förfrågan måste innehålla exakt en anteckningslista.",
            details={"reason": "missing_notes"},
        )
    try:
        draft_id = UUID(draft_id_values[0])
    except ValueError as error:
        raise validation_error(
            "Utkast-id:t är inte en giltig identifierare.",
            details={"reason": "invalid_draft_id"},
        ) from error
    try:
        raw_notes = json.loads(notes_values[0])
    except json.JSONDecodeError as error:
        raise validation_error(
            "Anteckningarna är inte giltiga.",
            details={"reason": "invalid_notes"},
        ) from error
    try:
        notes = tuple(_NOTES_ADAPTER.validate_python(raw_notes))
    except ValidationError as error:
        raise validation_error(
            "Anteckningarna är inte giltiga.",
            details={"reason": "invalid_notes"},
        ) from error

    assets_by_id: dict[str, bytes] = {}
    for field_name, content in uploaded_parts:
        if not field_name.startswith(_ASSET_FIELD_PREFIX):
            raise validation_error(
                "Bildfiler ska skickas som asset:<bild-id>.",
                details={"reason": "unknown_field", "field": field_name},
            )
        asset_id = field_name[len(_ASSET_FIELD_PREFIX) :]
        if not asset_id or asset_id in assets_by_id:
            raise asset_mismatch_error(asset_id)
        assets_by_id[asset_id] = content

    return (
        draft_id,
        parse_native_exam_document(document_values[0].encode("utf-8")),
        assets_by_id,
        notes,
    )
