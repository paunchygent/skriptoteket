from __future__ import annotations

from skriptoteket.protocols.llm import ChatMessage

_TEXT_CHARS_PER_TOKEN = 4
_CODE_CHARS_PER_TOKEN = 2


def estimate_text_tokens(text: str) -> int:
    if not text:
        return 0
    return (len(text) + _TEXT_CHARS_PER_TOKEN - 1) // _TEXT_CHARS_PER_TOKEN


def _keep_head(text: str, max_chars: int) -> str:
    if max_chars <= 0:
        return ""
    if len(text) <= max_chars:
        return text
    return text[:max_chars]


def _keep_tail(text: str, max_chars: int) -> str:
    if max_chars <= 0:
        return ""
    if len(text) <= max_chars:
        return text
    return text[-max_chars:]


def _code_tokens_for_text(text: str) -> int:
    if not text:
        return 0
    return (len(text) + _CODE_CHARS_PER_TOKEN - 1) // _CODE_CHARS_PER_TOKEN


def _budget_prompt_tokens(
    *, context_window_tokens: int, max_output_tokens: int, safety_margin_tokens: int
) -> int:
    budget = context_window_tokens - max_output_tokens - safety_margin_tokens
    return budget if budget > 0 else 0


def _consume_overflow(tokens: int, overflow: int) -> tuple[int, int]:
    if overflow <= 0:
        return tokens, 0
    if tokens <= 0:
        return 0, overflow
    reduction = overflow if overflow < tokens else tokens
    return tokens - reduction, overflow - reduction


def apply_inline_completion_budget(
    *,
    system_prompt: str,
    prefix: str,
    suffix: str,
    context_window_tokens: int,
    max_output_tokens: int,
    safety_margin_tokens: int,
    system_prompt_max_tokens: int,
    prefix_max_tokens: int,
    suffix_max_tokens: int,
) -> tuple[str, str, str]:
    prompt_budget_tokens = _budget_prompt_tokens(
        context_window_tokens=context_window_tokens,
        max_output_tokens=max_output_tokens,
        safety_margin_tokens=safety_margin_tokens,
    )

    target_total_tokens = system_prompt_max_tokens + prefix_max_tokens + suffix_max_tokens
    overflow = target_total_tokens - prompt_budget_tokens
    if overflow > 0:
        prefix_max_tokens, overflow = _consume_overflow(prefix_max_tokens, overflow)
        suffix_max_tokens, overflow = _consume_overflow(suffix_max_tokens, overflow)
        system_prompt_max_tokens, overflow = _consume_overflow(system_prompt_max_tokens, overflow)

    max_system_chars = system_prompt_max_tokens * _TEXT_CHARS_PER_TOKEN
    max_prefix_chars = prefix_max_tokens * _CODE_CHARS_PER_TOKEN
    max_suffix_chars = suffix_max_tokens * _CODE_CHARS_PER_TOKEN

    system_prompt = _keep_head(system_prompt, max_system_chars)
    prefix = _keep_tail(prefix, max_prefix_chars)
    suffix = _keep_head(suffix, max_suffix_chars)
    return system_prompt, prefix, suffix


def apply_chat_budget(
    *,
    system_prompt: str,
    messages: list[ChatMessage],
    context_window_tokens: int,
    max_output_tokens: int,
    safety_margin_tokens: int,
    system_prompt_max_tokens: int,
) -> tuple[str, list[ChatMessage]]:
    del (
        system_prompt_max_tokens
    )  # enforced at prompt composition time; never truncate the system prompt here

    prompt_budget_tokens = _budget_prompt_tokens(
        context_window_tokens=context_window_tokens,
        max_output_tokens=max_output_tokens,
        safety_margin_tokens=safety_margin_tokens,
    )

    system_prompt_tokens = estimate_text_tokens(system_prompt)

    available_message_tokens = prompt_budget_tokens - system_prompt_tokens
    if available_message_tokens <= 0:
        return system_prompt, []

    if not messages:
        return system_prompt, []

    token_costs = [estimate_text_tokens(message.content) for message in messages]
    total_tokens = sum(token_costs)

    start = 0
    while start < len(messages) and total_tokens > available_message_tokens:
        total_tokens -= token_costs[start]
        start += 1

    kept = messages[start:]
    while kept and kept[0].role == "assistant":
        kept = kept[1:]
    return system_prompt, kept


def apply_chat_ops_budget(
    *,
    system_prompt: str,
    messages: list[ChatMessage],
    user_payload: str,
    context_window_tokens: int,
    max_output_tokens: int,
    safety_margin_tokens: int,
    system_prompt_max_tokens: int,
) -> tuple[str, list[ChatMessage], bool]:
    del (
        system_prompt_max_tokens
    )  # enforced at prompt composition time; never truncate the system prompt here

    prompt_budget_tokens = _budget_prompt_tokens(
        context_window_tokens=context_window_tokens,
        max_output_tokens=max_output_tokens,
        safety_margin_tokens=safety_margin_tokens,
    )

    system_prompt_tokens = estimate_text_tokens(system_prompt)
    user_payload_tokens = _code_tokens_for_text(user_payload)

    available_message_tokens = prompt_budget_tokens - system_prompt_tokens - user_payload_tokens
    if available_message_tokens <= 0:
        return system_prompt, [], False

    if not messages:
        return system_prompt, [], True

    token_costs = [estimate_text_tokens(message.content) for message in messages]
    total_tokens = sum(token_costs)

    start = 0
    while start < len(messages) and total_tokens > available_message_tokens:
        total_tokens -= token_costs[start]
        start += 1

    kept = messages[start:]
    while kept and kept[0].role == "assistant":
        kept = kept[1:]
    return system_prompt, kept, True
