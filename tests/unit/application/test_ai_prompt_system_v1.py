from __future__ import annotations

import pytest

from skriptoteket.application.editor.prompt_composer import (
    PromptTemplateError,
    compose_system_prompt,
    compose_system_prompt_from_template,
    validate_prompt_templates,
)
from skriptoteket.application.editor.prompt_templates import (
    CONTRACT_V2_FRAGMENT,
    PromptTemplate,
)
from skriptoteket.config import Settings
from skriptoteket.domain.scripting.ui.policy import DEFAULT_UI_POLICY
from tests.fixtures.application_fixtures import FakeTokenCounter


@pytest.mark.unit
def test_validate_prompt_templates_passes() -> None:
    validate_prompt_templates(settings=Settings(), token_counter=FakeTokenCounter())


@pytest.mark.unit
def test_compose_system_prompt_resolves_all_placeholders_and_includes_policy_values() -> None:
    settings = Settings()
    composed = compose_system_prompt(
        template_id="inline_completion_v1",
        settings=settings,
        token_counter=FakeTokenCounter(),
    )

    assert "{{" not in composed.text
    assert "## Contract v2 (Skriptoteket UI)" in composed.text
    assert f"- max outputs: {DEFAULT_UI_POLICY.caps.max_outputs}" in composed.text
    assert (
        f"- total ui_payload max: {DEFAULT_UI_POLICY.budgets.ui_payload_max_bytes} bytes"
        in composed.text
    )
    assert f"- Timeout: {settings.RUNNER_TIMEOUT_SANDBOX_SECONDS}s (sandbox)" in composed.text


@pytest.mark.unit
def test_compose_system_prompt_raises_when_required_placeholder_missing() -> None:
    settings = Settings()
    template = PromptTemplate(
        template_id="test_template",
        capability="inline_completion",
        template_path="ignored",
        required_placeholders=frozenset({CONTRACT_V2_FRAGMENT}),
    )

    with pytest.raises(PromptTemplateError, match="missing required placeholders"):
        compose_system_prompt_from_template(
            template=template,
            settings=settings,
            template_text_loader=lambda _path: "Hello world",
            token_counter=FakeTokenCounter(),
        )


@pytest.mark.unit
def test_compose_system_prompt_raises_when_unknown_placeholder_used() -> None:
    settings = Settings()
    template = PromptTemplate(
        template_id="test_template",
        capability="inline_completion",
        template_path="ignored",
        required_placeholders=frozenset(),
    )

    with pytest.raises(PromptTemplateError, match="unknown placeholders"):
        compose_system_prompt_from_template(
            template=template,
            settings=settings,
            template_text_loader=lambda _path: "Hello {{UNKNOWN_FRAGMENT}} world",
            token_counter=FakeTokenCounter(),
        )


@pytest.mark.unit
def test_compose_system_prompt_raises_when_budget_exceeded() -> None:
    settings = Settings(LLM_COMPLETION_SYSTEM_PROMPT_MAX_TOKENS=1)
    template = PromptTemplate(
        template_id="test_template",
        capability="inline_completion",
        template_path="ignored",
        required_placeholders=frozenset({CONTRACT_V2_FRAGMENT}),
    )

    with pytest.raises(PromptTemplateError, match="exceeds budget"):
        compose_system_prompt_from_template(
            template=template,
            settings=settings,
            template_text_loader=lambda _path: "{{CONTRACT_V2_FRAGMENT}}",
            token_counter=FakeTokenCounter(),
        )
