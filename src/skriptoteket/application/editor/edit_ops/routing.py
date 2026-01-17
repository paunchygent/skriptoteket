from __future__ import annotations

from skriptoteket.config import Settings
from skriptoteket.protocols.llm import ChatFailoverDecision, ChatOpsProvidersProtocol


def can_use_fallback(
    *,
    providers: ChatOpsProvidersProtocol,
    allow_remote_fallback: bool,
) -> bool:
    return providers.fallback is not None and (
        allow_remote_fallback or not providers.fallback_is_remote
    )


def resolve_model_for_counting(
    *,
    settings: Settings,
    decision: ChatFailoverDecision,
) -> str:
    if decision.provider == "fallback":
        return settings.LLM_CHAT_OPS_FALLBACK_MODEL.strip() or settings.LLM_CHAT_OPS_MODEL
    return settings.LLM_CHAT_OPS_MODEL


def resolve_fallback_model_for_counting(*, settings: Settings) -> str:
    return settings.LLM_CHAT_OPS_FALLBACK_MODEL.strip() or settings.LLM_CHAT_OPS_MODEL
