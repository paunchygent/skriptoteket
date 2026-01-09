from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Mapping

from skriptoteket.application.editor.ai_prompt import load_system_prompt_text
from skriptoteket.application.editor.prompt_budget import estimate_text_tokens
from skriptoteket.application.editor.prompt_fragments import (
    contract_v2_fragment,
    helpers_fragment,
    runner_constraints_fragment,
)
from skriptoteket.application.editor.prompt_templates import (
    CONTRACT_V2_FRAGMENT,
    HELPERS_FRAGMENT,
    RUNNER_CONSTRAINTS_FRAGMENT,
    PromptCapability,
    PromptTemplate,
    get_prompt_template,
)
from skriptoteket.config import Settings

_PLACEHOLDER_PATTERN = re.compile(r"\{\{([A-Z0-9_]+)\}\}")


class PromptTemplateError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class ComposedSystemPrompt:
    template_id: str
    capability: PromptCapability
    text: str
    estimated_tokens: int


TemplateTextLoader = Callable[[str], str]


def _find_placeholders(template_text: str) -> set[str]:
    return {match.group(1) for match in _PLACEHOLDER_PATTERN.finditer(template_text)}


def _replace_placeholders(*, template_text: str, fragments: Mapping[str, str]) -> str:
    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in fragments:
            raise PromptTemplateError(f"Unknown placeholder: {name}")
        return fragments[name]

    return _PLACEHOLDER_PATTERN.sub(replace, template_text)


def _system_prompt_max_tokens(*, settings: Settings, capability: PromptCapability) -> int:
    if capability == "inline_completion":
        return settings.LLM_COMPLETION_SYSTEM_PROMPT_MAX_TOKENS
    if capability == "edit_suggestion":
        return settings.LLM_EDIT_SYSTEM_PROMPT_MAX_TOKENS
    if capability == "chat_stream":
        return settings.LLM_CHAT_SYSTEM_PROMPT_MAX_TOKENS
    if capability == "chat_ops":
        return settings.LLM_CHAT_OPS_SYSTEM_PROMPT_MAX_TOKENS
    raise ValueError(f"Unknown PromptCapability: {capability}")


def build_default_fragments(*, settings: Settings) -> dict[str, str]:
    return {
        CONTRACT_V2_FRAGMENT: contract_v2_fragment(),
        RUNNER_CONSTRAINTS_FRAGMENT: runner_constraints_fragment(settings=settings),
        HELPERS_FRAGMENT: helpers_fragment(),
    }


def compose_system_prompt(*, template_id: str, settings: Settings) -> ComposedSystemPrompt:
    try:
        template = get_prompt_template(template_id=template_id)
    except ValueError as exc:
        raise PromptTemplateError(str(exc)) from exc

    return compose_system_prompt_from_template(template=template, settings=settings)


def compose_system_prompt_from_template(
    *,
    template: PromptTemplate,
    settings: Settings,
    template_text_loader: TemplateTextLoader | None = None,
) -> ComposedSystemPrompt:
    def default_loader(prompt_path: str) -> str:
        return load_system_prompt_text(prompt_path=prompt_path)

    loader = template_text_loader or default_loader

    try:
        template_text = loader(template.template_path)
    except OSError as exc:
        raise PromptTemplateError(
            f"Failed to load prompt template '{template.template_id}'."
        ) from exc

    placeholders = _find_placeholders(template_text)

    missing_required = template.required_placeholders - placeholders
    if missing_required:
        raise PromptTemplateError(
            "Prompt template is missing required placeholders: "
            + ", ".join(sorted(missing_required))
        )

    fragments = build_default_fragments(settings=settings)
    unknown = placeholders - fragments.keys()
    if unknown:
        raise PromptTemplateError(
            "Prompt template uses unknown placeholders: " + ", ".join(sorted(unknown))
        )

    composed = _replace_placeholders(template_text=template_text, fragments=fragments)
    unresolved = _find_placeholders(composed)
    if unresolved:
        raise PromptTemplateError(
            "Prompt template composition left unresolved placeholders: "
            + ", ".join(sorted(unresolved))
        )

    system_prompt_max_tokens = _system_prompt_max_tokens(
        settings=settings,
        capability=template.capability,
    )
    estimated_tokens = estimate_text_tokens(composed)
    if estimated_tokens > system_prompt_max_tokens:
        raise PromptTemplateError(
            "Composed system prompt exceeds budget "
            f"({estimated_tokens} > {system_prompt_max_tokens})."
        )

    return ComposedSystemPrompt(
        template_id=template.template_id,
        capability=template.capability,
        text=composed,
        estimated_tokens=estimated_tokens,
    )


def validate_prompt_templates(*, settings: Settings) -> None:
    """Validate that all prompt templates compose cleanly under current settings.

    Intended for unit tests (fail fast) and optional startup diagnostics.
    """

    from skriptoteket.application.editor.prompt_templates import PROMPT_TEMPLATES

    for template_id in PROMPT_TEMPLATES:
        compose_system_prompt(template_id=template_id, settings=settings)
