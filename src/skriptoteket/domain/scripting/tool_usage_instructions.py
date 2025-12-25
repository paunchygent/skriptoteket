from __future__ import annotations

import hashlib

USAGE_INSTRUCTIONS_SESSION_CONTEXT = "ui:usage_instructions"
USAGE_INSTRUCTIONS_SEEN_HASH_KEY = "seen_hash"


def compute_usage_instructions_hash_or_none(*, usage_instructions: str | None) -> str | None:
    if usage_instructions is None:
        return None

    normalized = usage_instructions.replace("\r\n", "\n").strip()
    if not normalized:
        return None

    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
