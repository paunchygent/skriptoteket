from __future__ import annotations

from typing import Protocol
from uuid import UUID


class IdGeneratorProtocol(Protocol):
    def new_uuid(self) -> UUID: ...
