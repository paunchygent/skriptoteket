from __future__ import annotations

import json
import re

from pydantic import BaseModel, ConfigDict, ValidationError

from skriptoteket.protocols.edit_ops_payload_parser import (
    EditOpsParsedPayload,
    EditOpsPayloadParserProtocol,
)
from skriptoteket.protocols.llm import EditOpsOp

_CODE_FENCE_PATTERN = re.compile(r"```[a-zA-Z0-9_-]*\n(.*?)```", re.DOTALL)


def _extract_first_fenced_block(text: str) -> str | None:
    match = _CODE_FENCE_PATTERN.search(text)
    if not match:
        return None
    return match.group(1)


def _extract_json_object(text: str) -> str | None:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    return text[start : end + 1]


class _EditOpsPayload(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    assistant_message: str
    ops: list[EditOpsOp]


class DefaultEditOpsPayloadParser(EditOpsPayloadParserProtocol):
    def parse(self, *, raw: str) -> EditOpsParsedPayload | None:
        candidates = [raw.strip()]
        fenced = _extract_first_fenced_block(raw)
        if fenced:
            candidates.append(fenced.strip())
        extracted = _extract_json_object(raw)
        if extracted:
            candidates.append(extracted.strip())

        for candidate in candidates:
            if not candidate:
                continue
            try:
                payload = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            try:
                parsed = _EditOpsPayload.model_validate(payload)
            except ValidationError:
                continue
            return EditOpsParsedPayload(
                assistant_message=parsed.assistant_message,
                ops=parsed.ops,
            )

        return None
