from __future__ import annotations

from dataclasses import dataclass

from skriptoteket.config import Settings
from skriptoteket.infrastructure.llm.model_families import is_gpt5_family_model
from skriptoteket.protocols.llm import (
    ChatFailoverProvider,
    ChatOpsBudget,
    ChatOpsBudgetResolverProtocol,
)


@dataclass(frozen=True, slots=True)
class SettingsBasedChatOpsBudgetResolver(ChatOpsBudgetResolverProtocol):
    settings: Settings

    def resolve_chat_ops_budget(self, *, provider: ChatFailoverProvider) -> ChatOpsBudget:
        if provider == "fallback":
            model = (
                self.settings.LLM_CHAT_OPS_FALLBACK_MODEL.strip()
                or self.settings.LLM_CHAT_OPS_MODEL
            )
        else:
            model = self.settings.LLM_CHAT_OPS_MODEL

        if is_gpt5_family_model(model=model):
            return ChatOpsBudget(
                context_window_tokens=self.settings.LLM_CHAT_OPS_GPT5_CONTEXT_WINDOW_TOKENS,
                max_output_tokens=self.settings.LLM_CHAT_OPS_GPT5_MAX_TOKENS,
            )

        return ChatOpsBudget(
            context_window_tokens=self.settings.LLM_CHAT_OPS_CONTEXT_WINDOW_TOKENS,
            max_output_tokens=self.settings.LLM_CHAT_OPS_MAX_TOKENS,
        )
