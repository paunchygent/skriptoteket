from __future__ import annotations


def _normalize_model_name(model: str) -> str:
    normalized = model.strip().lower()
    if normalized.startswith("openai/"):
        return normalized[len("openai/") :]
    return normalized


def _matches_prefix(*, normalized: str, prefix: str) -> bool:
    if not normalized.startswith(prefix):
        return False
    end = len(prefix)
    return end == len(normalized) or normalized[end] in "-_."


def is_gpt5_family_model(*, model: str) -> bool:
    normalized = model.strip().lower()
    if not normalized:
        return False

    prefixes = ("gpt-5", "openai/gpt-5")
    for prefix in prefixes:
        if not normalized.startswith(prefix):
            continue
        end = len(prefix)
        if end == len(normalized) or normalized[end] in "-_.":
            return True

    return False


def supports_stop_sequences(*, model: str) -> bool:
    normalized = _normalize_model_name(model)
    if not normalized:
        return False
    if _matches_prefix(normalized=normalized, prefix="gpt-5-nano"):
        return False
    return True


def supports_prompt_cache_retention(*, model: str) -> bool:
    normalized = _normalize_model_name(model)
    if not normalized:
        return False
    if _matches_prefix(normalized=normalized, prefix="gpt-5-nano"):
        return False

    allowed_prefixes = (
        "gpt-5.2",
        "gp5-5.1-codex-max",
        "gpt-5.1-codex",
        "gpt-5.1-codex-mini",
        "gpt-5.1-chat-latest",
        "gpt-5.1",
        "gpt-5-codex",
        "gpt-5",
        "gpt-4.1",
    )

    for prefix in allowed_prefixes:
        if _matches_prefix(normalized=normalized, prefix=prefix):
            return True

    return False


def supports_prompt_cache_key(*, model: str) -> bool:
    normalized = _normalize_model_name(model)
    if not normalized:
        return False
    if _matches_prefix(normalized=normalized, prefix="gpt-5-nano"):
        return False

    # Conservative allowlist: only send when we also support retention semantics.
    return supports_prompt_cache_retention(model=model)
