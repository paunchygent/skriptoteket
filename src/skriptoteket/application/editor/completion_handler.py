from __future__ import annotations

from collections.abc import Callable

from skriptoteket.application.editor.completion.flow import InlineCompletionFlow
from skriptoteket.config import Settings
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.llm import (
    InlineCompletionCommand,
    InlineCompletionHandlerProtocol,
    InlineCompletionProvidersProtocol,
    InlineCompletionResult,
)
from skriptoteket.protocols.llm_captures import LlmCaptureStoreProtocol
from skriptoteket.protocols.token_counter import TokenCounterResolverProtocol


class InlineCompletionHandler(InlineCompletionHandlerProtocol):
    def __init__(
        self,
        *,
        settings: Settings,
        providers: InlineCompletionProvidersProtocol,
        capture_store: LlmCaptureStoreProtocol,
        token_counters: TokenCounterResolverProtocol,
        system_prompt_loader: Callable[[str, str], str] | None = None,
    ) -> None:
        self._flow = InlineCompletionFlow(
            settings=settings,
            providers=providers,
            capture_store=capture_store,
            token_counters=token_counters,
            system_prompt_loader=system_prompt_loader,
        )

    async def handle(
        self,
        *,
        actor: User,
        command: InlineCompletionCommand,
    ) -> InlineCompletionResult:
        return await self._flow.handle(actor=actor, command=command)
