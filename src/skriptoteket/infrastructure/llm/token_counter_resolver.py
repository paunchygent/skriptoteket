from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import structlog

from skriptoteket.config import Settings
from skriptoteket.infrastructure.llm.model_families import is_gpt5_family_model
from skriptoteket.protocols.llm import ChatMessageRole
from skriptoteket.protocols.token_counter import TokenCounterProtocol, TokenCounterResolverProtocol

logger = structlog.get_logger(__name__)


def _looks_like_devstral_model(model: str) -> bool:
    normalized = model.strip().lower()
    return "devstral" in normalized or "mistral" in normalized


@lru_cache(maxsize=1)
def _find_packaged_tekken_json_path() -> Path | None:
    try:
        import mistral_common  # type: ignore[import-not-found]
    except ImportError:
        return None

    data_dir = Path(mistral_common.__file__).resolve().parent / "data"
    if not data_dir.is_dir():
        return None

    candidates = sorted(data_dir.glob("tekken_*.json"))
    if not candidates:
        return None

    # Prefer the newest date-based file name (lexicographically stable).
    return max(candidates, key=lambda path: path.name)


@dataclass(frozen=True, slots=True)
class _ChatOverheads:
    system_message_tokens: int
    non_system_message_tokens: int


class HeuristicTokenCounter(TokenCounterProtocol):
    def __init__(self, *, overheads: _ChatOverheads, chars_per_token: int = 4) -> None:
        self._overheads = overheads
        self._chars_per_token = max(1, chars_per_token)

    def count_text(self, text: str) -> int:
        if not text:
            return 0
        # Conservative, stable fallback (previous estimate_text_tokens behavior).
        return (len(text) + self._chars_per_token - 1) // self._chars_per_token

    def truncate_text_head(self, *, text: str, max_tokens: int) -> str:
        if max_tokens <= 0 or not text:
            return ""
        max_chars = max_tokens * self._chars_per_token
        return text if len(text) <= max_chars else text[:max_chars]

    def truncate_text_tail(self, *, text: str, max_tokens: int) -> str:
        if max_tokens <= 0 or not text:
            return ""
        max_chars = max_tokens * self._chars_per_token
        return text if len(text) <= max_chars else text[-max_chars:]

    def count_system_prompt(self, *, content: str) -> int:
        if not content:
            return 0
        return self._overheads.system_message_tokens + self.count_text(content)

    def count_chat_message(self, *, role: ChatMessageRole, content: str) -> int:
        if not content:
            return self._overheads.non_system_message_tokens
        return self._overheads.non_system_message_tokens + self.count_text(content)


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


class TekkenTokenCounter(TokenCounterProtocol):
    def __init__(self, *, tekken_json_path: Path, overheads: _ChatOverheads) -> None:
        self._tekken_json_path = tekken_json_path
        self._overheads = overheads

    @property
    @lru_cache(maxsize=1)
    def _tokenizer(self):
        from mistral_common.tokens.tokenizers.tekken import Tekkenizer

        return Tekkenizer.from_file(str(self._tekken_json_path))

    def count_text(self, text: str) -> int:
        if not text:
            return 0
        return len(self._tokenizer.encode(text, bos=False, eos=False))

    def truncate_text_head(self, *, text: str, max_tokens: int) -> str:
        if max_tokens <= 0 or not text:
            return ""
        tokens = self._tokenizer.encode(text, bos=False, eos=False)
        if len(tokens) <= max_tokens:
            return text
        return str(self._tokenizer.decode(tokens[:max_tokens]))

    def truncate_text_tail(self, *, text: str, max_tokens: int) -> str:
        if max_tokens <= 0 or not text:
            return ""
        tokens = self._tokenizer.encode(text, bos=False, eos=False)
        if len(tokens) <= max_tokens:
            return text
        return str(self._tokenizer.decode(tokens[-max_tokens:]))

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
    settings: Settings

    @property
    def _gpt5_overheads(self) -> _ChatOverheads:
        return _ChatOverheads(
            system_message_tokens=self.settings.LLM_GPT5_SYSTEM_MESSAGE_OVERHEAD_TOKENS,
            non_system_message_tokens=self.settings.LLM_GPT5_MESSAGE_OVERHEAD_TOKENS,
        )

    @property
    def _devstral_overheads(self) -> _ChatOverheads:
        return _ChatOverheads(
            system_message_tokens=self.settings.LLM_DEVSTRAL_SYSTEM_MESSAGE_OVERHEAD_TOKENS,
            non_system_message_tokens=self.settings.LLM_DEVSTRAL_MESSAGE_OVERHEAD_TOKENS,
        )

    @property
    def _heuristic_overheads(self) -> _ChatOverheads:
        return _ChatOverheads(
            system_message_tokens=self.settings.LLM_HEURISTIC_SYSTEM_MESSAGE_OVERHEAD_TOKENS,
            non_system_message_tokens=self.settings.LLM_HEURISTIC_MESSAGE_OVERHEAD_TOKENS,
        )

    @lru_cache(maxsize=32)
    def for_model(self, *, model: str) -> TokenCounterProtocol:
        normalized = model.strip()
        if is_gpt5_family_model(model=normalized):
            return TiktokenTokenCounter(model=normalized, overheads=self._gpt5_overheads)

        if _looks_like_devstral_model(normalized):
            tekken_json_path = self.settings.LLM_DEVSTRAL_TEKKEN_JSON_PATH
            if tekken_json_path and tekken_json_path.is_file():
                return TekkenTokenCounter(
                    tekken_json_path=tekken_json_path,
                    overheads=self._devstral_overheads,
                )

            inferred_path = _find_packaged_tekken_json_path()
            if inferred_path and inferred_path.is_file():
                logger.info(
                    "llm_tokenizer_assets_auto_selected",
                    tokenizer="tekken",
                    model=normalized,
                    tekken_json_path=inferred_path.name,
                    source="mistral_common",
                )
                return TekkenTokenCounter(
                    tekken_json_path=inferred_path,
                    overheads=self._devstral_overheads,
                )

            logger.warning(
                "llm_tokenizer_assets_missing",
                tokenizer="tekken",
                model=normalized,
                tekken_json_path=str(tekken_json_path) if tekken_json_path else None,
                fallback="heuristic",
            )
            return HeuristicTokenCounter(overheads=self._heuristic_overheads, chars_per_token=2)

        return HeuristicTokenCounter(overheads=self._heuristic_overheads)
