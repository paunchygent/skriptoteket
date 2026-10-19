"""The native exam document's stored JSON bytes, written and read back."""

import json

from pydantic import ValidationError

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NATIVE_EXAM_DOCUMENT_SCHEMA_VERSION,
    NativeExamDocument,
)
from skriptoteket.domain.errors import DomainError, ErrorCode


def native_exam_document_json_bytes(document: NativeExamDocument) -> bytes:
    payload = document.model_dump(mode="json")
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def parse_native_exam_document(data: bytes) -> NativeExamDocument:
    try:
        payload = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise DomainError(
            code=ErrorCode.VALIDATION_ERROR,
            message="Native exam document payload is not valid JSON.",
        ) from error
    if isinstance(payload, dict):
        version = payload.get("schema_version")
        if version is None:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Native exam document payload is missing schema_version.",
            )
        if version != NATIVE_EXAM_DOCUMENT_SCHEMA_VERSION:
            raise DomainError(
                code=ErrorCode.DOCUMENT_SCHEMA_OUTDATED,
                message="Native exam document uses an outdated schema version.",
                details={"schema_version": version},
            )
    try:
        return NativeExamDocument.model_validate(payload)
    except ValidationError as error:
        raise DomainError(
            code=ErrorCode.VALIDATION_ERROR,
            message="Native exam document payload failed validation.",
            details={"errors": error.error_count()},
        ) from error
