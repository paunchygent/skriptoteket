from __future__ import annotations

from collections.abc import Callable
from functools import lru_cache
from pathlib import Path

import httpx
import structlog

from skriptoteket.config import Settings
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.role_guards import require_at_least_role
from skriptoteket.protocols.llm import (
    InlineCompletionCommand,
    InlineCompletionHandlerProtocol,
    InlineCompletionProviderProtocol,
    InlineCompletionResult,
    LLMCompletionRequest,
)

logger = structlog.get_logger(__name__)

_PREFIX_MAX_CHARS = 8000
_SUFFIX_MAX_CHARS = 4000


def _resolve_kb_path() -> Path:
    # Repo layout: <root>/src/skriptoteket/application/editor/completion_handler.py
    root = Path(__file__).resolve().parents[4]
    return root / "docs/reference/ref-ai-script-generation-kb.md"


@lru_cache(maxsize=1)
def _load_kb_text() -> str:
    path = _resolve_kb_path()
    return path.read_text(encoding="utf-8")


def _build_system_prompt(kb_text: str) -> str:
    return (
        "You are an AI code completion assistant for Skriptoteket.\n"
        "Return ONLY the code that should be inserted at the cursor.\n"
        "- No markdown\n"
        "- No explanations\n"
        "- Preserve indentation and newlines\n"
        "- Prefer Swedish user-facing messages\n\n"
        "Knowledge base:\n"
        f"{kb_text}\n"
    )


def _trim_prefix(prefix: str) -> str:
    if len(prefix) <= _PREFIX_MAX_CHARS:
        return prefix
    return prefix[-_PREFIX_MAX_CHARS:]


def _trim_suffix(suffix: str) -> str:
    if len(suffix) <= _SUFFIX_MAX_CHARS:
        return suffix
    return suffix[:_SUFFIX_MAX_CHARS]


class InlineCompletionHandler(InlineCompletionHandlerProtocol):
    def __init__(
        self,
        *,
        settings: Settings,
        provider: InlineCompletionProviderProtocol,
        kb_loader: Callable[[], str] = _load_kb_text,
    ) -> None:
        self._settings = settings
        self._provider = provider
        self._kb_loader = kb_loader

    async def handle(
        self,
        *,
        actor: User,
        command: InlineCompletionCommand,
    ) -> InlineCompletionResult:
        require_at_least_role(user=actor, role=Role.CONTRIBUTOR)

        if not self._settings.LLM_COMPLETION_ENABLED:
            return InlineCompletionResult(completion="", enabled=False)

        try:
            kb_text = self._kb_loader()
        except OSError:
            logger.warning("ai_completion_kb_unavailable")
            return InlineCompletionResult(completion="", enabled=False)

        system_prompt = _build_system_prompt(kb_text)
        request = LLMCompletionRequest(
            prefix=_trim_prefix(command.prefix),
            suffix=_trim_suffix(command.suffix),
        )

        try:
            response = await self._provider.complete_inline(
                request=request,
                system_prompt=system_prompt,
            )
        except (httpx.TimeoutException, httpx.RequestError):
            logger.info(
                "ai_inline_completion_failed",
                prefix_len=len(request.prefix),
                suffix_len=len(request.suffix),
                user_id=str(actor.id),
            )
            return InlineCompletionResult(completion="", enabled=True)

        if response.finish_reason == "length":
            return InlineCompletionResult(completion="", enabled=True)

        completion = response.completion
        if completion and completion.lstrip().startswith("```"):
            completion = ""

        return InlineCompletionResult(completion=completion, enabled=True)
