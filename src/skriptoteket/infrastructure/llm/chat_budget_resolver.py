from __future__ import annotations

from dataclasses import dataclass

from skriptoteket.config import Settings
from skriptoteket.infrastructure.llm.model_families import is_gpt5_family_model
from skriptoteket.protocols.llm import (
    ChatBudget,
    ChatBudgetResolverProtocol,
    ChatFailoverProvider,
)


@dataclass(frozen=True, slots=True)
class SettingsBasedChatBudgetResolver(ChatBudgetResolverProtocol):
    settings: Settings

    def resolve_chat_budget(self, *, provider: ChatFailoverProvider) -> ChatBudget:
        if provider == "fallback":
            model = self.settings.LLM_CHAT_FALLBACK_MODEL.strip() or self.settings.LLM_CHAT_MODEL
        else:
            model = self.settings.LLM_CHAT_MODEL

        if is_gpt5_family_model(model=model):
            return ChatBudget(
                context_window_tokens=self.settings.LLM_CHAT_GPT5_CONTEXT_WINDOW_TOKENS,
                max_output_tokens=self.settings.LLM_CHAT_GPT5_MAX_TOKENS,
            )

        return ChatBudget(
            context_window_tokens=self.settings.LLM_CHAT_CONTEXT_WINDOW_TOKENS,
            max_output_tokens=self.settings.LLM_CHAT_MAX_TOKENS,
        )
