from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from skriptoteket.config import Settings
from skriptoteket.protocols.llm import ChatMessageRole
from skriptoteket.protocols.token_counter import TokenCounterProtocol, TokenCounterResolverProtocol


@dataclass(frozen=True, slots=True)
class _ChatOverheads:
    system_message_tokens: int
    non_system_message_tokens: int


class TiktokenTokenCounter(TokenCounterProtocol):
    def __init__(self, *, model: str, overheads: _ChatOverheads) -> None:
        self._model = model
        self._overheads = overheads

    @property
    @lru_cache(maxsize=1)
    def _encoding(self):
        import tiktoken

        try:
            return tiktoken.encoding_for_model(self._model)
        except KeyError:
            # Conservative fallback when the model name is unknown to tiktoken.
            return tiktoken.get_encoding("o200k_base")

    def count_text(self, text: str) -> int:
        if not text:
            return 0
        return len(self._encoding.encode(text))

    def truncate_text_head(self, *, text: str, max_tokens: int) -> str:
        if max_tokens <= 0 or not text:
            return ""
        tokens = self._encoding.encode(text)
        if len(tokens) <= max_tokens:
            return text
        return str(self._encoding.decode(tokens[:max_tokens]))

    def truncate_text_tail(self, *, text: str, max_tokens: int) -> str:
        if max_tokens <= 0 or not text:
            return ""
        tokens = self._encoding.encode(text)
        if len(tokens) <= max_tokens:
            return text
        return str(self._encoding.decode(tokens[-max_tokens:]))

    def count_system_prompt(self, *, content: str) -> int:
        if not content:
            return 0
        return self._overheads.system_message_tokens + self.count_text(content)

    def count_chat_message(self, *, role: ChatMessageRole, content: str) -> int:
        if not content:
            return self._overheads.non_system_message_tokens
        return self._overheads.non_system_message_tokens + self.count_text(content)


@dataclass(frozen=True, slots=True, eq=False)
class SettingsBasedTokenCounterResolver(TokenCounterResolverProtocol):
    """Every editor model is an OpenAI model, so every model gets tiktoken."""

    settings: Settings

    @property
    def _overheads(self) -> _ChatOverheads:
        return _ChatOverheads(
            system_message_tokens=self.settings.LLM_GPT5_SYSTEM_MESSAGE_OVERHEAD_TOKENS,
            non_system_message_tokens=self.settings.LLM_GPT5_MESSAGE_OVERHEAD_TOKENS,
        )

    @lru_cache(maxsize=32)
    def for_model(self, *, model: str) -> TokenCounterProtocol:
        return TiktokenTokenCounter(model=model.strip(), overheads=self._overheads)
