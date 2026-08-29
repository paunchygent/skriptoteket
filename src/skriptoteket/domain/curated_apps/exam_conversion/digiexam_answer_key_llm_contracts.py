"""Structured-LLM contracts for DigiExam answer-key completion.

Purpose:
    Define the typed request/completion boundary between answer-key candidate
    planning and remote structured-output providers, ported from
    sir-convert-a-lot `76983339` and trimmed to the JSON-Schema-only lane.

Relationships:
    - Consumed by `domain.curated_apps.exam_conversion.digiexam_answer_key_completion`
      for candidate planning and by the httpx provider adapter in
      `infrastructure.llm.openai.answer_key_structured_provider`.
    - The provider protocol seam lives in `protocols.exam_answer_key`.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from pydantic import JsonValue


class StructuredLLMEndpointKind(StrEnum):
    """Supported structured provider endpoint families."""

    RESPONSES = "responses"
    CHAT_COMPLETIONS = "chat_completions"


class StructuredLLMReasoningEffort(StrEnum):
    """Provider reasoning-effort settings when supported by the endpoint."""

    NONE = "none"
    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    XHIGH = "xhigh"


class StructuredLLMTextVerbosity(StrEnum):
    """Provider text-verbosity settings when supported by the endpoint."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class StructuredLLMBackendFailureCode(StrEnum):
    """Stable provider/backend failure codes for enrichment outcomes."""

    PROVIDER_CONFIG_MISSING = "provider_config_missing"
    PROVIDER_TIMEOUT = "provider_timeout"
    PROVIDER_REQUEST_FAILED = "provider_request_failed"
    PROVIDER_HTTP_ERROR = "provider_http_error"
    PROVIDER_INVALID_JSON = "provider_invalid_json"
    PROVIDER_RESPONSE_NOT_OBJECT = "provider_response_not_object"
    PROVIDER_EMPTY_CONTENT = "provider_empty_content"
    PROVIDER_CONTENT_NOT_JSON = "provider_content_not_json"
    PROVIDER_SCHEMA_MISMATCH = "provider_schema_mismatch"
    PROVIDER_REFUSAL = "provider_refusal"


@dataclass(frozen=True)
class StructuredOutputSpec:
    """Item-local JSON Schema for one structured answer-key decision."""

    schema_name: str
    schema_version: str
    json_schema: dict[str, JsonValue]
    strict: bool = True

    def __post_init__(self) -> None:
        if not self.schema_name.strip():
            raise ValueError("Structured output schema_name must be non-empty.")
        if not self.schema_version.strip():
            raise ValueError("Structured output schema_version must be non-empty.")
        if self.json_schema.get("type") != "object":
            raise ValueError("Structured output JSON Schema must describe an object.")
        if self.strict and self.json_schema.get("additionalProperties") is not False:
            raise ValueError(
                "Strict structured output schemas must set additionalProperties=false."
            )


@dataclass(frozen=True)
class StructuredLLMProviderProfile:
    """Metadata profile for one configured structured-output provider."""

    provider_id: str
    model: str
    endpoint_kind: StructuredLLMEndpointKind
    is_remote: bool
    context_window_tokens: int
    max_output_tokens: int
    temperature: float = 0.0
    reasoning_effort: StructuredLLMReasoningEffort | None = None
    text_verbosity: StructuredLLMTextVerbosity | None = None

    def __post_init__(self) -> None:
        if not self.provider_id.strip():
            raise ValueError("Structured provider_id must be non-empty.")
        if not self.model.strip():
            raise ValueError("Structured provider model must be non-empty.")
        if self.context_window_tokens <= 0:
            raise ValueError("Structured provider context_window_tokens must be positive.")
        if self.max_output_tokens <= 0:
            raise ValueError("Structured provider max_output_tokens must be positive.")
        if self.max_output_tokens >= self.context_window_tokens:
            raise ValueError(
                "Structured provider max_output_tokens must be below context_window_tokens."
            )
        if self.temperature < 0 or self.temperature > 2:
            raise ValueError("Structured provider temperature must be between 0 and 2.")


@dataclass(frozen=True)
class StructuredLLMRequest:
    """Single-turn item-local structured-output request."""

    job_id: str
    item_id: str
    item_type: str
    prompt_template_version: str
    system_prompt: str
    user_payload: str
    output_spec: StructuredOutputSpec
    estimated_input_tokens: int
    max_output_tokens: int

    def __post_init__(self) -> None:
        if not self.job_id.strip():
            raise ValueError("Structured LLM job_id must be non-empty.")
        if not self.item_id.strip():
            raise ValueError("Structured LLM item_id must be non-empty.")
        if not self.item_type.strip():
            raise ValueError("Structured LLM item_type must be non-empty.")
        if not self.prompt_template_version.strip():
            raise ValueError("Structured LLM prompt_template_version must be non-empty.")
        if not self.system_prompt.strip():
            raise ValueError("Structured LLM system_prompt must be non-empty.")
        if not self.user_payload.strip():
            raise ValueError("Structured LLM user_payload must be non-empty.")
        if self.estimated_input_tokens < 0:
            raise ValueError("Structured LLM estimated_input_tokens cannot be negative.")
        if self.max_output_tokens <= 0:
            raise ValueError("Structured LLM max_output_tokens must be positive.")


@dataclass(frozen=True)
class StructuredLLMUsage:
    """Optional bounded usage metadata returned by a provider."""

    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None

    @property
    def usable_total_tokens(self) -> int | None:
        """Provider-reported total usable for lease reconciliation, if any."""

        if self.total_tokens is not None and self.total_tokens >= 0:
            return self.total_tokens
        if (
            self.prompt_tokens is not None
            and self.completion_tokens is not None
            and self.prompt_tokens >= 0
            and self.completion_tokens >= 0
        ):
            return self.prompt_tokens + self.completion_tokens
        return None


@dataclass(frozen=True)
class StructuredLLMResponse:
    """Provider response after JSON parsing and backend validation."""

    content: dict[str, JsonValue]
    finish_reason: str | None
    usage: StructuredLLMUsage = StructuredLLMUsage()


class StructuredLLMProviderError(Exception):
    """Typed provider failure that never stores raw prompts or responses."""

    def __init__(
        self,
        *,
        failure_code: StructuredLLMBackendFailureCode,
        message: str,
        provider_id: str,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.failure_code = failure_code
        self.provider_id = provider_id
        self.status_code = status_code


def estimate_prompt_tokens(text: str) -> int:
    """Estimate prompt tokens with the sircon-pinned chars/4 ceiling heuristic."""

    return max(1, (len(text) + 3) // 4)
