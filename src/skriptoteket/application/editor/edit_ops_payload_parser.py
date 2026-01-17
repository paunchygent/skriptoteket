from __future__ import annotations

import json
import re

from pydantic import BaseModel, ConfigDict, ValidationError

from skriptoteket.protocols.edit_ops_payload_parser import (
    EditOpsParsedPayload,
    EditOpsPayloadParserProtocol,
)
from skriptoteket.protocols.llm import EditOpsOp

_CODE_FENCE_PATTERN = re.compile(r"(?ms)^\s*```[a-zA-Z0-9_-]*\s*\n(.*?)^\s*```\s*$")


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


def _split_patch_lines(lines: list[str]) -> list[str]:
    normalized: list[str] = []
    for line in lines:
        if "\n" in line or "\r" in line:
            parts = line.replace("\r\n", "\n").replace("\r", "\n").split("\n")
            for part in parts:
                if part == "":
                    continue
                normalized.append(part)
        else:
            normalized.append(line)
    return normalized


def _normalize_patch_lines(payload: dict) -> None:
    ops = payload.get("ops")
    if not isinstance(ops, list):
        return
    for op in ops:
        if not isinstance(op, dict):
            continue
        if op.get("op") != "patch":
            continue
        lines = op.get("patch_lines")
        if not isinstance(lines, list) or not lines:
            continue
        if not any(isinstance(item, str) and ("\n" in item or "\r" in item) for item in lines):
            continue
        op["patch_lines"] = _split_patch_lines([item for item in lines if isinstance(item, str)])


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
            if isinstance(payload, dict):
                _normalize_patch_lines(payload)
            try:
                parsed = _EditOpsPayload.model_validate(payload)
            except ValidationError:
                continue
            return EditOpsParsedPayload(
                assistant_message=parsed.assistant_message,
                ops=parsed.ops,
            )

        return None
