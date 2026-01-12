from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

PromptCapability = Literal["inline_completion", "chat_stream", "chat_ops"]


CONTRACT_V2_FRAGMENT = "CONTRACT_V2_FRAGMENT"
HELPERS_FRAGMENT = "HELPERS_FRAGMENT"
RUNNER_CONSTRAINTS_FRAGMENT = "RUNNER_CONSTRAINTS_FRAGMENT"


@dataclass(frozen=True, slots=True)
class PromptTemplate:
    template_id: str
    capability: PromptCapability
    template_path: str
    required_placeholders: frozenset[str]


PROMPT_TEMPLATES: dict[str, PromptTemplate] = {
    "inline_completion_v1": PromptTemplate(
        template_id="inline_completion_v1",
        capability="inline_completion",
        template_path="src/skriptoteket/application/editor/system_prompts/inline_completion_v1.txt",
        required_placeholders=frozenset(
            {
                CONTRACT_V2_FRAGMENT,
                RUNNER_CONSTRAINTS_FRAGMENT,
                HELPERS_FRAGMENT,
            }
        ),
    ),
    "editor_chat_v1": PromptTemplate(
        template_id="editor_chat_v1",
        capability="chat_stream",
        template_path="src/skriptoteket/application/editor/system_prompts/editor_chat_v1.txt",
        required_placeholders=frozenset(
            {
                CONTRACT_V2_FRAGMENT,
                RUNNER_CONSTRAINTS_FRAGMENT,
                HELPERS_FRAGMENT,
            }
        ),
    ),
    "editor_chat_ops_v1": PromptTemplate(
        template_id="editor_chat_ops_v1",
        capability="chat_ops",
        template_path="src/skriptoteket/application/editor/system_prompts/editor_chat_ops_v1.txt",
        required_placeholders=frozenset(
            {
                CONTRACT_V2_FRAGMENT,
                RUNNER_CONSTRAINTS_FRAGMENT,
                HELPERS_FRAGMENT,
            }
        ),
    ),
}


def get_prompt_template(*, template_id: str) -> PromptTemplate:
    try:
        return PROMPT_TEMPLATES[template_id]
    except KeyError as exc:
        raise ValueError(f"Unknown prompt template id: {template_id}") from exc
