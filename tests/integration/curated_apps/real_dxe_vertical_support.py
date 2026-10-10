"""External-provider and worker wiring for the real-DXE integration vertical."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

from dishka import Provider, Scope, provide
from pydantic import BaseModel, ConfigDict, JsonValue
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.application.curated_apps.exam_converter_correction_sessions import (
    ExamConverterCorrectionIntentWrite,
)
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
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_ir_contracts import (
    DigiExamIrItem,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_source_fingerprints import (
    source_item_fingerprint,
)
from skriptoteket.domain.curated_apps.exam_converter_correction_sessions import (
    ExamConverterCorrectionSourceBinding,
    ExamConverterCorrectionTarget,
)
from skriptoteket.domain.identity.models import AuthProvider, Role, User
from skriptoteket.infrastructure.db.models.user import UserModel
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


def json_artifact(content: bytes) -> dict[str, JsonValue]:
    decoded = json.loads(content)
    assert isinstance(decoded, dict)
    return decoded


def parse_review_rows(content: bytes) -> dict[str, dict[str, JsonValue]]:
    document = json_artifact(content)
    raw_rows = document.get("items")
    assert isinstance(raw_rows, list)
    rows: dict[str, dict[str, JsonValue]] = {}
    for raw in raw_rows:
        assert isinstance(raw, dict)
        item_id = raw.get("item_id")
        assert isinstance(item_id, str)
        rows[item_id] = raw
    return rows


def accepted_intent(
    *,
    item: DigiExamIrItem,
    row: dict[str, JsonValue],
    binding: ExamConverterCorrectionSourceBinding,
) -> ExamConverterCorrectionIntentWrite:
    answer = row["answer_payload"]
    assert isinstance(answer, dict)
    lineage = {
        key: row[key]
        for key in (
            "candidate_id",
            "candidate_payload_digest",
            "prompt_template_version",
            "provider_profile_id",
            "schema_name",
            "schema_version",
        )
    }
    lineage.update({"completion_report_sha256": None, "validation_state": "valid"})
    if item.item_type is DigiExamItemType.GAP_FILL:
        kind = "manual_gap_open_cloze_answer_key"
        interaction_id = f"gap-{item.item_id}"
        payload = {"gap_answers": answer["gap_answers"]}
    else:
        kind = "manual_choice_answer_key"
        interaction_id = f"choice-{item.item_id}"
        raw_ids = answer["correct_alternative_ids"]
        assert isinstance(raw_ids, list)
        payload = {"correct_choice_ids": [f"choice-{value}" for value in raw_ids]}
    payload.update(
        {
            "interaction_id": interaction_id,
            "submission_origin": "accepted_advisory_candidate",
            "candidate_lineage": lineage,
        }
    )
    return ExamConverterCorrectionIntentWrite(
        entry_id=f"accept-{item.item_id}",
        source_binding=binding,
        item_id=item.item_id,
        sequence=item.sequence,
        item_type=item.item_type.value,
        source_item_fingerprint=source_item_fingerprint(item),
        kind=kind,
        target=ExamConverterCorrectionTarget(interaction_id=interaction_id),
        payload=payload,
    )


def manual_intent(
    *, item: DigiExamIrItem, binding: ExamConverterCorrectionSourceBinding
) -> ExamConverterCorrectionIntentWrite:
    answer: dict[str, JsonValue]
    if item.item_type is DigiExamItemType.GAP_FILL:
        kind = "manual_gap_open_cloze_answer_key"
        interaction_id = f"gap-{item.item_id}"
        answer = {
            "gap_answers": [
                {"gap_id": gap.guid, "accepted_values": [f"Manuellt svar {index}"]}
                for index, gap in enumerate(item.gaps, start=1)
            ]
        }
    else:
        kind = "manual_choice_answer_key"
        interaction_id = f"choice-{item.item_id}"
        assert item.alternatives
        answer = {"correct_choice_ids": [f"choice-{item.alternatives[0].id}"]}
    answer.update(
        {
            "interaction_id": interaction_id,
            "submission_origin": "teacher_authored",
            "candidate_lineage": None,
        }
    )
    return ExamConverterCorrectionIntentWrite(
        entry_id=f"manual-{item.item_id}",
        source_binding=binding,
        item_id=item.item_id,
        sequence=item.sequence,
        item_type=item.item_type.value,
        source_item_fingerprint=source_item_fingerprint(item),
        kind=kind,
        target=ExamConverterCorrectionTarget(interaction_id=interaction_id),
        payload=answer,
    )


async def create_actor(db_session: AsyncSession) -> User:
    now = datetime.now(UTC)
    actor = User(
        id=uuid4(),
        email=f"real-dxe-{uuid4()}@example.test",
        role=Role.USER,
        auth_provider=AuthProvider.LOCAL,
        created_at=now,
        updated_at=now,
    )
    db_session.add(
        UserModel(
            id=actor.id,
            email=actor.email,
            password_hash="integration-only",
            role=actor.role,
            auth_provider=actor.auth_provider,
            created_at=now,
            updated_at=now,
        )
    )
    await db_session.commit()
    return actor
