"""The native exam document's stored JSON bytes, written and read back."""

import json

from pydantic import ValidationError

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
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
    try:
        return NativeExamDocument.model_validate(payload)
    except ValidationError as error:
        raise DomainError(
            code=ErrorCode.VALIDATION_ERROR,
            message="Native exam document payload failed validation.",
            details={"errors": error.error_count()},
        ) from error
