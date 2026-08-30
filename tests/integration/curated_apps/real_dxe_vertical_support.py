"""External-provider and worker wiring for the real-DXE integration vertical."""

from __future__ import annotations

from dishka import Provider, Scope, provide
from pydantic import BaseModel, ConfigDict, JsonValue

from skriptoteket.application.curated_apps.handlers.exam_answer_key_enrichment_jobs import (
    ProcessExamAnswerKeyEnrichmentJobHandler,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    AnswerKeyProviderRoute,
    StructuredLLMEndpointKind,
    StructuredLLMProviderProfile,
    StructuredLLMRequest,
    StructuredLLMResponse,
    StructuredLLMUsage,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_contracts import (
    DigiExamItemType,
)
from skriptoteket.protocols.exam_answer_key import (
    ExamAnswerKeyEnrichmentJobRepositoryProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class _ChoicePromptItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    item_id: str


class _ChoicePromptChoice(BaseModel):
    model_config = ConfigDict(extra="ignore")

    alternative_id: int


class _ChoicePrompt(BaseModel):
    model_config = ConfigDict(extra="ignore")

    item: _ChoicePromptItem
    choices: tuple[_ChoicePromptChoice, ...]


class RealRequestProviderBoundary:
    """Isolate only provider I/O while validating production-built requests."""

    def __init__(self, *, expected_item_ids: frozenset[str]) -> None:
        self._expected_item_ids = expected_item_ids
        self.requests: list[StructuredLLMRequest] = []

    async def complete_structured(
        self,
        *,
        request: StructuredLLMRequest,
        profile: StructuredLLMProviderProfile,
    ) -> StructuredLLMResponse:
        assert profile.provider_id == "integration-primary"
        assert request.item_id in self._expected_item_ids
        assert request.item_id not in {seen.item_id for seen in self.requests}
        self.requests.append(request)
        if request.item_type == DigiExamItemType.GAP_FILL.value:
            required = request.output_spec.json_schema["required"]
            assert isinstance(required, list)
            content: dict[str, JsonValue] = {
                str(key): f"Integrationssvar {key}" for key in required
            }
        else:
            prompt = _ChoicePrompt.model_validate_json(request.user_payload)
            assert prompt.item.item_id == request.item_id
            assert prompt.choices
            content = {"correct_alternative_ids": [prompt.choices[0].alternative_id]}
        return StructuredLLMResponse(
            content=content,
            finish_reason="stop",
            usage=StructuredLLMUsage(total_tokens=17),
        )


class WorkerProvider(Provider):
    def __init__(
        self,
        *,
        handler: ProcessExamAnswerKeyEnrichmentJobHandler,
        jobs: ExamAnswerKeyEnrichmentJobRepositoryProtocol,
        uow: UnitOfWorkProtocol,
    ) -> None:
        super().__init__()
        self._handler = handler
        self._jobs = jobs
        self._uow = uow

    @provide(scope=Scope.REQUEST)
    def handler(self) -> ProcessExamAnswerKeyEnrichmentJobHandler:
        return self._handler

    @provide(scope=Scope.REQUEST)
    def jobs(self) -> ExamAnswerKeyEnrichmentJobRepositoryProtocol:
        return self._jobs

    @provide(scope=Scope.REQUEST)
    def uow(self) -> UnitOfWorkProtocol:
        return self._uow


def provider_route() -> AnswerKeyProviderRoute:
    return AnswerKeyProviderRoute(
        primary=StructuredLLMProviderProfile(
            provider_id="integration-primary",
            model="integration-structured-model",
            endpoint_kind=StructuredLLMEndpointKind.RESPONSES,
            is_remote=True,
            context_window_tokens=32_000,
            max_output_tokens=512,
        ),
        failover=StructuredLLMProviderProfile(
            provider_id="integration-failover",
            model="integration-failover-model",
            endpoint_kind=StructuredLLMEndpointKind.CHAT_COMPLETIONS,
            is_remote=True,
            context_window_tokens=32_000,
            max_output_tokens=512,
        ),
    )
