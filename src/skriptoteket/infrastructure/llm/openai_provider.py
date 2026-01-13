"""OpenAI-compatible provider implementations (stable import path).

The implementation is split into smaller modules under `infrastructure/llm/openai/`.
This module re-exports the public provider classes to avoid churn in DI wiring and tests.
"""

from __future__ import annotations

from skriptoteket.infrastructure.llm.openai.chat_ops_provider import OpenAIChatOpsProvider
from skriptoteket.infrastructure.llm.openai.chat_stream_provider import OpenAIChatStreamProvider
from skriptoteket.infrastructure.llm.openai.inline_completion_provider import (
    OpenAIInlineCompletionProvider,
)

__all__ = [
    "OpenAIChatOpsProvider",
    "OpenAIChatStreamProvider",
    "OpenAIInlineCompletionProvider",
]
