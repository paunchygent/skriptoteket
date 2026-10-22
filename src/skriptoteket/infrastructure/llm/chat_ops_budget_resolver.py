from __future__ import annotations

from dataclasses import dataclass

from skriptoteket.config import Settings
from skriptoteket.protocols.llm import ChatOpsBudget, ChatOpsBudgetResolverProtocol


@dataclass(frozen=True, slots=True)
class SettingsBasedChatOpsBudgetResolver(ChatOpsBudgetResolverProtocol):
    settings: Settings

    def resolve_chat_ops_budget(self) -> ChatOpsBudget:
        return ChatOpsBudget(
            context_window_tokens=self.settings.LLM_CHAT_OPS_CONTEXT_WINDOW_TOKENS,
            max_output_tokens=self.settings.LLM_CHAT_OPS_MAX_TOKENS,
        )
