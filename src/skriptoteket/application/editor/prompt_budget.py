from __future__ import annotations

from skriptoteket.protocols.llm import ChatMessage
from skriptoteket.protocols.token_counter import TokenCounterProtocol


def _is_virtual_file_context_message(message: ChatMessage) -> bool:
    meta = message.meta
    return isinstance(meta, dict) and meta.get("kind") == "virtual_file_context"


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
    token_counter: TokenCounterProtocol,
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

    system_prompt = token_counter.truncate_text_head(
        text=system_prompt, max_tokens=system_prompt_max_tokens
    )
    prefix = token_counter.truncate_text_tail(text=prefix, max_tokens=prefix_max_tokens)
    suffix = token_counter.truncate_text_head(text=suffix, max_tokens=suffix_max_tokens)
    return system_prompt, prefix, suffix


def apply_chat_budget(
    *,
    system_prompt: str,
    messages: list[ChatMessage],
    context_window_tokens: int,
    max_output_tokens: int,
    safety_margin_tokens: int,
    system_prompt_max_tokens: int,
    token_counter: TokenCounterProtocol,
) -> tuple[str, list[ChatMessage]]:
    del (
        system_prompt_max_tokens
    )  # enforced at prompt composition time; never truncate the system prompt here

    prompt_budget_tokens = _budget_prompt_tokens(
        context_window_tokens=context_window_tokens,
        max_output_tokens=max_output_tokens,
        safety_margin_tokens=safety_margin_tokens,
    )

    system_prompt_tokens = token_counter.count_system_prompt(content=system_prompt)

    available_message_tokens = prompt_budget_tokens - system_prompt_tokens
    if available_message_tokens <= 0:
        return system_prompt, []

    if not messages:
        return system_prompt, []

    token_costs = [
        token_counter.count_chat_message(role=message.role, content=message.content)
        for message in messages
    ]
    total_tokens = sum(token_costs)

    start = 0
    while start < len(messages) and total_tokens > available_message_tokens:
        total_tokens -= token_costs[start]
        start += 1

    kept = messages[start:]
    while kept and kept[0].role == "assistant" and not _is_virtual_file_context_message(kept[0]):
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
    token_counter: TokenCounterProtocol,
) -> tuple[str, list[ChatMessage], bool]:
    del (
        system_prompt_max_tokens
    )  # enforced at prompt composition time; never truncate the system prompt here

    prompt_budget_tokens = _budget_prompt_tokens(
        context_window_tokens=context_window_tokens,
        max_output_tokens=max_output_tokens,
        safety_margin_tokens=safety_margin_tokens,
    )

    system_prompt_tokens = token_counter.count_system_prompt(content=system_prompt)
    user_payload_tokens = token_counter.count_chat_message(role="user", content=user_payload)

    available_message_tokens = prompt_budget_tokens - system_prompt_tokens - user_payload_tokens
    if available_message_tokens <= 0:
        return system_prompt, [], False

    if not messages:
        return system_prompt, [], True

    token_costs = [
        token_counter.count_chat_message(role=message.role, content=message.content)
        for message in messages
    ]
    total_tokens = sum(token_costs)

    start = 0
    while start < len(messages) and total_tokens > available_message_tokens:
        total_tokens -= token_costs[start]
        start += 1

    kept = messages[start:]
    while kept and kept[0].role == "assistant" and not _is_virtual_file_context_message(kept[0]):
        kept = kept[1:]
    return system_prompt, kept, True
