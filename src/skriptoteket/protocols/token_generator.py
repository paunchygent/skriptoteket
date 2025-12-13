from __future__ import annotations

from typing import Protocol


class TokenGeneratorProtocol(Protocol):
    def new_token(self) -> str: ...
