from __future__ import annotations

from skriptoteket.protocols.llm import ChatMessageRole
from skriptoteket.protocols.token_counter import TokenCounterProtocol, TokenCounterResolverProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class FakeUow(UnitOfWorkProtocol):
    """Fake Unit of Work for unit tests.

    Tracks enter/exit states for verification.
    """

    def __init__(self) -> None:
        self.entered = False
        self.exited = False

    async def __aenter__(self) -> UnitOfWorkProtocol:
        self.entered = True
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        self.exited = True


class FakeTokenCounter(TokenCounterProtocol):
    """Cheap, deterministic token counter for unit tests.

    Uses a stable chars-per-token heuristic and supports token-aware truncation.
    """

    def __init__(
        self, *, system_overhead_tokens: int = 0, message_overhead_tokens: int = 0
    ) -> None:
        self._system_overhead_tokens = system_overhead_tokens
        self._message_overhead_tokens = message_overhead_tokens

    def count_text(self, text: str) -> int:
        if not text:
            return 0
        return (len(text) + 4 - 1) // 4

    def truncate_text_head(self, *, text: str, max_tokens: int) -> str:
        if max_tokens <= 0 or not text:
            return ""
        max_chars = max_tokens * 4
        return text if len(text) <= max_chars else text[:max_chars]

    def truncate_text_tail(self, *, text: str, max_tokens: int) -> str:
        if max_tokens <= 0 or not text:
            return ""
        max_chars = max_tokens * 4
        return text if len(text) <= max_chars else text[-max_chars:]

    def count_system_prompt(self, *, content: str) -> int:
        if not content:
            return 0
        return self._system_overhead_tokens + self.count_text(content)

    def count_chat_message(self, *, role: ChatMessageRole, content: str) -> int:
        del role
        return self._message_overhead_tokens + self.count_text(content)


class FakeTokenCounterResolver(TokenCounterResolverProtocol):
    def __init__(self, *, token_counter: TokenCounterProtocol | None = None) -> None:
        self._token_counter = token_counter or FakeTokenCounter()

    def for_model(self, *, model: str) -> TokenCounterProtocol:
        del model
        return self._token_counter
