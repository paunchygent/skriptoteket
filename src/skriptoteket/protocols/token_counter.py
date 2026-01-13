from __future__ import annotations

from typing import Protocol

from skriptoteket.protocols.llm import ChatMessageRole


class TokenCounterProtocol(Protocol):
    """Token counting + token-aware truncation.

    Implementations MUST be deterministic and MUST NOT require network access.
    """

    def count_text(self, text: str) -> int: ...

    def truncate_text_head(self, *, text: str, max_tokens: int) -> str: ...

    def truncate_text_tail(self, *, text: str, max_tokens: int) -> str: ...

    def count_system_prompt(self, *, content: str) -> int: ...

    def count_chat_message(self, *, role: ChatMessageRole, content: str) -> int: ...


class TokenCounterResolverProtocol(Protocol):
    def for_model(self, *, model: str) -> TokenCounterProtocol: ...
