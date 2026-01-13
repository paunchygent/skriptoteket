from __future__ import annotations


def resolve_fim_tokens(*, model: str) -> tuple[str, str, str]:
    model_lower = model.strip().lower()
    if "qwen" in model_lower:
        return ("<|fim_prefix|>", "<|fim_suffix|>", "<|fim_middle|>")
    if "codellama" in model_lower or "code-llama" in model_lower:
        return ("<PRE>", "<SUF>", "<MID>")
    if "starcoder" in model_lower:
        return ("<fim_prefix>", "<fim_suffix>", "<fim_middle>")
    return ("<|fim_prefix|>", "<|fim_suffix|>", "<|fim_middle|>")


def build_fim_prompt(*, prefix: str, suffix: str, model: str) -> str:
    prefix_token, suffix_token, middle_token = resolve_fim_tokens(model=model)
    return f"{prefix_token}{prefix}{suffix_token}{suffix}{middle_token}"
