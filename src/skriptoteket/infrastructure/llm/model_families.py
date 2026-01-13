from __future__ import annotations


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
