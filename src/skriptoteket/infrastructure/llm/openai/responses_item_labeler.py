"""Responses adapter for the second item-type labeling pass B (TASK-SKRIPT-39-05-04).

Purpose:
    Decide one question's label alone (D23 pass B): gpt-6-luna at medium
    reasoning effort and low verbosity answers a label-only schema object whose
    ``label`` property carries the label descriptions. Ported from variant B of
    the hard-item experiment, measured 2026-10-11. Timeouts, 429 and 5xx retry
    with bounded exponential backoff; a provider refusal becomes an unresolved,
    refused label. No request content or API key is logged.

Relationships:
    Implements ``protocols.item_type_labeler.SecondPassItemTypeLabelerProtocol``
    over ``protocols.exam_answer_key.AnswerKeyStructuredProviderProtocol``. The
    user payload and label descriptions come from
    ``infrastructure.llm.openai.decisions_item_labeler``; the profile comes from
    ``docx_conversion_profiles.build_luna_item_label_profile``.
    ``application.curated_apps.item_type_labeling`` wraps it with the token lease.
"""

from __future__ import annotations

import json
from uuid import UUID

from pydantic import JsonValue

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMBackendFailureCode,
    StructuredLLMProviderError,
    StructuredLLMProviderProfile,
    StructuredLLMRequest,
    StructuredOutputSpec,
    estimate_prompt_tokens,
)
from skriptoteket.infrastructure.llm.openai.decisions_item_labeler import (
    LABEL_DESCRIPTIONS,
    build_second_pass_payload,
)
from skriptoteket.protocols.exam_answer_key import AnswerKeyStructuredProviderProtocol
from skriptoteket.protocols.item_type_labeler import (
    ItemTypeLabel,
    ItemTypeLabelerError,
    LabelingItem,
    SecondPassItemTypeLabelerProtocol,
    SecondPassLabel,
)
from skriptoteket.protocols.sleeper import SleeperProtocol

SYSTEM_PROMPT = (
    "Select exactly one supported label for the target question. Return only the schema object."
)
PROMPT_TEMPLATE_VERSION = "item_type_label_b_v1"
_LABELS_BY_VALUE = {label.value: label for label in ItemTypeLabel}


def _label_schema() -> dict[str, JsonValue]:
    return {
        "type": "object",
        "properties": {
            "label": {
                "type": "string",
                "enum": [label.value for label in ItemTypeLabel],
                "description": "\n".join(
                    f"{label.value}: {LABEL_DESCRIPTIONS[label]}" for label in ItemTypeLabel
                ),
            }
        },
        "required": ["label"],
        "additionalProperties": False,
    }


def build_second_pass_request(
    *, job_id: UUID, item: LabelingItem, profile: StructuredLLMProviderProfile
) -> StructuredLLMRequest:
    user_payload = build_second_pass_payload(item)["input"]
    if not isinstance(user_payload, str):
        raise TypeError("Second-pass payload input must be a string.")
    schema = _label_schema()
    return StructuredLLMRequest(
        job_id=str(job_id),
        item_id=f"label_b:{item.item_id}",
        item_type="item_type_label",
        prompt_template_version=PROMPT_TEMPLATE_VERSION,
        system_prompt=SYSTEM_PROMPT,
        user_payload=user_payload,
        output_spec=StructuredOutputSpec("item_type_label", "1", schema),
        estimated_input_tokens=estimate_prompt_tokens(
            SYSTEM_PROMPT + user_payload + json.dumps(schema)
        ),
        max_output_tokens=profile.max_output_tokens,
    )


def _is_transient(error: StructuredLLMProviderError) -> bool:
    if error.failure_code is StructuredLLMBackendFailureCode.PROVIDER_TIMEOUT:
        return True
    status = error.status_code
    return (
        error.failure_code is StructuredLLMBackendFailureCode.PROVIDER_HTTP_ERROR
        and status is not None
        and (status == 429 or 500 <= status <= 599)
    )


class ResponsesSecondPassItemTypeLabeler(SecondPassItemTypeLabelerProtocol):
    """Holds no lease; the caller meters tokens around ``label_one``."""

    def __init__(
        self,
        *,
        provider: AnswerKeyStructuredProviderProtocol,
        profile: StructuredLLMProviderProfile,
        sleeper: SleeperProtocol,
        max_attempts: int = 3,
        max_delay_seconds: float = 8.0,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("Second-pass labeler max_attempts must be at least 1.")
        self._provider = provider
        self._profile = profile
        self._sleeper = sleeper
        self._max_attempts = max_attempts
        self._max_delay_seconds = max_delay_seconds

    @property
    def provider_profile_id(self) -> str:
        return self._profile.provider_id

    def estimate_tokens(self, *, item: LabelingItem) -> int:
        request = build_second_pass_request(job_id=UUID(int=0), item=item, profile=self._profile)
        return request.estimated_input_tokens + self._profile.max_output_tokens

    async def label_one(self, *, job_id: UUID, item: LabelingItem) -> SecondPassLabel:
        request = build_second_pass_request(job_id=job_id, item=item, profile=self._profile)
        attempt = 0
        while True:
            attempt += 1
            try:
                response = await self._provider.complete_structured(
                    request=request, profile=self._profile
                )
            except StructuredLLMProviderError as error:
                if error.failure_code is StructuredLLMBackendFailureCode.PROVIDER_REFUSAL:
                    return SecondPassLabel(
                        label=ItemTypeLabel.UNRESOLVED,
                        input_tokens=None,
                        output_tokens=None,
                        refused=True,
                    )
                if _is_transient(error) and attempt < self._max_attempts:
                    await self._sleeper.sleep(min(2 ** (attempt - 1), self._max_delay_seconds))
                    continue
                raise ItemTypeLabelerError(
                    code=error.failure_code.value,
                    message=f"Second-pass labeling failed after {attempt} attempt(s).",
                    status_code=error.status_code,
                ) from error
            if response.finish_reason not in {None, "completed"}:
                raise ItemTypeLabelerError(
                    code="incomplete", message="Second-pass response did not complete."
                )
            value = response.content.get("label")
            label = _LABELS_BY_VALUE.get(value) if isinstance(value, str) else None
            if set(response.content) != {"label"} or label is None:
                raise ItemTypeLabelerError(
                    code="schema_mismatch",
                    message="Second-pass response is not exactly one known label.",
                )
            return SecondPassLabel(
                label=label,
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
            )
