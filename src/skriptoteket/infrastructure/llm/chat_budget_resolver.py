from __future__ import annotations

from dataclasses import dataclass

from skriptoteket.config import Settings
from skriptoteket.protocols.llm import ChatBudget, ChatBudgetResolverProtocol


@dataclass(frozen=True, slots=True)
class SettingsBasedChatBudgetResolver(ChatBudgetResolverProtocol):
    settings: Settings

    def resolve_chat_budget(self) -> ChatBudget:
        return ChatBudget(
            context_window_tokens=self.settings.LLM_CHAT_CONTEXT_WINDOW_TOKENS,
            max_output_tokens=self.settings.LLM_CHAT_MAX_TOKENS,
        )
