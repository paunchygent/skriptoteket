from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from skriptoteket.protocols.llm import EditOpsOp


@dataclass(frozen=True, slots=True)
class EditOpsParsedPayload:
    assistant_message: str
    ops: list[EditOpsOp]


class EditOpsPayloadParserProtocol(Protocol):
    def parse(self, *, raw: str) -> EditOpsParsedPayload | None: ...
