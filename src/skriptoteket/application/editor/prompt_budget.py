from __future__ import annotations

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


def apply_edit_suggestion_budget(
    *,
    system_prompt: str,
    instruction: str,
    prefix: str,
    selection: str,
    suffix: str,
    context_window_tokens: int,
    max_output_tokens: int,
    safety_margin_tokens: int,
    system_prompt_max_tokens: int,
    instruction_max_tokens: int,
    selection_max_tokens: int,
    prefix_max_tokens: int,
    suffix_max_tokens: int,
) -> tuple[str, str, str, str, str]:
    prompt_budget_tokens = _budget_prompt_tokens(
        context_window_tokens=context_window_tokens,
        max_output_tokens=max_output_tokens,
        safety_margin_tokens=safety_margin_tokens,
    )

    target_total_tokens = (
        system_prompt_max_tokens
        + instruction_max_tokens
        + selection_max_tokens
        + prefix_max_tokens
        + suffix_max_tokens
    )
    overflow = target_total_tokens - prompt_budget_tokens
    if overflow > 0:
        prefix_max_tokens, overflow = _consume_overflow(prefix_max_tokens, overflow)
        suffix_max_tokens, overflow = _consume_overflow(suffix_max_tokens, overflow)
        instruction_max_tokens, overflow = _consume_overflow(instruction_max_tokens, overflow)
        selection_max_tokens, overflow = _consume_overflow(selection_max_tokens, overflow)
        system_prompt_max_tokens, overflow = _consume_overflow(system_prompt_max_tokens, overflow)

    selection_tokens_needed = _code_tokens_for_text(selection)
    code_pool_tokens = selection_max_tokens + prefix_max_tokens + suffix_max_tokens

    if selection_tokens_needed > code_pool_tokens:
        max_selection_chars = code_pool_tokens * _CODE_CHARS_PER_TOKEN
        selection = _keep_head(selection, max_selection_chars)
        prefix = ""
        suffix = ""
        prefix_max_tokens = 0
        suffix_max_tokens = 0
        selection_max_tokens = code_pool_tokens
    else:
        extra_needed = selection_tokens_needed - selection_max_tokens
        if extra_needed > 0:
            take_from_suffix = (
                extra_needed if extra_needed < suffix_max_tokens else suffix_max_tokens
            )
            suffix_max_tokens -= take_from_suffix
            selection_max_tokens += take_from_suffix
            extra_needed -= take_from_suffix

            if extra_needed > 0:
                take_from_prefix = (
                    extra_needed if extra_needed < prefix_max_tokens else prefix_max_tokens
                )
                prefix_max_tokens -= take_from_prefix
                selection_max_tokens += take_from_prefix

    max_system_chars = system_prompt_max_tokens * _TEXT_CHARS_PER_TOKEN
    max_instruction_chars = instruction_max_tokens * _TEXT_CHARS_PER_TOKEN
    max_selection_chars = selection_max_tokens * _CODE_CHARS_PER_TOKEN
    max_prefix_chars = prefix_max_tokens * _CODE_CHARS_PER_TOKEN
    max_suffix_chars = suffix_max_tokens * _CODE_CHARS_PER_TOKEN

    system_prompt = _keep_head(system_prompt, max_system_chars)
    instruction = _keep_head(instruction, max_instruction_chars)
    selection = _keep_head(selection, max_selection_chars)
    prefix = _keep_tail(prefix, max_prefix_chars)
    suffix = _keep_head(suffix, max_suffix_chars)
    return system_prompt, instruction, prefix, selection, suffix
