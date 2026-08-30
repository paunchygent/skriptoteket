"""Real-input PostgreSQL vertical for partial DigiExam answer-key enrichment."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from dishka import make_async_container
from pydantic import JsonValue
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJobStatus,
)
from skriptoteket.application.curated_apps.exam_conversion_producers import (
    InProcessExamConversionProducer,
    parse_source_exam,
)
from skriptoteket.application.curated_apps.exam_converter_correction_sessions import (
    ExamConverterCorrectionIntentWrite,
    ReplaceExamConverterCorrectionIntentsRequest,
)
from skriptoteket.application.curated_apps.handlers.conversion_hub_jobs import (
    ConversionHubUpload,
)
from skriptoteket.application.curated_apps.handlers.exam_answer_key_enrichment_jobs import (
    ProcessExamAnswerKeyEnrichmentJobHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_converter_conversions import (
    CreateExamConverterConversionJobsHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_converter_correction_sessions import (
    ReplaceExamConverterCorrectionIntentsHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_converter_product import (
    ExamConverterProductHandler,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_completion import (
    item_is_enrichable,
    plan_answer_key_enrichment,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_contracts import (
    DigiExamAnswerKeyProvenance,
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
from skriptoteket.infrastructure.clock import UTCClock
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_conversion_artifacts import (
    FilesystemExamConversionArtifactStore,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_pdf_renderer import (
    WeasyPrintExamNetPdfRenderer,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_qti_writer import (
    ExamNetQtiPackageWriter,
)
from skriptoteket.infrastructure.db.models.exam_answer_key_enrichment_job import (
    ExamAnswerKeyEnrichmentJobModel,
)
from skriptoteket.infrastructure.db.models.exam_answer_key_token_lease import (
    ExamAnswerKeyTokenLeaseModel,
)
from skriptoteket.infrastructure.db.models.user import UserModel
from skriptoteket.infrastructure.db.uow import SQLAlchemyUnitOfWork
from skriptoteket.infrastructure.id_generator import UUID4Generator
from skriptoteket.infrastructure.llm.answer_key_provider_selection import (
    FixedRouteAnswerKeyProviderSelector,
)
from skriptoteket.infrastructure.repositories.conversion_hub_jobs import (
    PostgreSQLConversionHubJobRepository,
)
from skriptoteket.infrastructure.repositories.exam_answer_key_enrichment_jobs import (
    PostgreSQLExamAnswerKeyEnrichmentJobRepository,
)
from skriptoteket.infrastructure.repositories.exam_answer_key_proposed_overlays import (
    PostgreSQLExamAnswerKeyProposedOverlayRepository,
)
from skriptoteket.infrastructure.repositories.exam_answer_key_token_leases import (
    PostgreSQLAnswerKeyTokenLeaseRepository,
)
from skriptoteket.infrastructure.repositories.exam_converter_correction_sessions import (
    PostgreSQLExamConverterCorrectionSessionRepository,
)
from skriptoteket.workers.exam_answer_key_enrichment import (
    process_next_answer_key_enrichment_job,
)
from tests.integration.curated_apps.real_dxe_vertical_support import (
    RealRequestProviderBoundary,
    WorkerProvider,
    provider_route,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.docker,
    pytest.mark.asyncio(loop_scope="module"),
]

_FIXTURE = Path("tests/fixtures/exam_conversion/real_inputs/1776888013-ak7-lag-och-ratt.dxe")
_FIXTURE_SHA256 = "ab39bbee54ec9004ce733e0942caa3c4934c37f87c7d35d59c9a16eca4f3839a"
_PARTIAL_FAILURE_CODE = "partial_enrichment_manual_follow_up_required"


def _json_artifact(content: bytes) -> dict[str, JsonValue]:
    decoded = json.loads(content)
    assert isinstance(decoded, dict)
    return decoded


def _review_rows(content: bytes) -> dict[str, dict[str, JsonValue]]:
    document = _json_artifact(content)
    raw_rows = document.get("items")
    assert isinstance(raw_rows, list)
    rows: dict[str, dict[str, JsonValue]] = {}
    for raw in raw_rows:
        assert isinstance(raw, dict)
        item_id = raw.get("item_id")
        assert isinstance(item_id, str)
        rows[item_id] = raw
    return rows


def _accepted_intent(
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


def _manual_intent(
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


async def _actor(db_session: AsyncSession) -> User:
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


async def test_real_dxe_crosses_postgres_worker_review_and_replay_vertical(
    db_session: AsyncSession,
    tmp_path: Path,
) -> None:
    source_bytes = _FIXTURE.read_bytes()
    assert hashlib.sha256(source_bytes).hexdigest() == _FIXTURE_SHA256
    upload = ConversionHubUpload(
        filename=_FIXTURE.name,
        content_type="application/octet-stream",
        file_bytes=source_bytes,
    )
    exam = parse_source_exam(upload=upload)
    plan = plan_answer_key_enrichment(exam)
    expected_provider_items = frozenset(
        item.item_id
        for item in exam.items
        if item.answer_key.provenance is DigiExamAnswerKeyProvenance.ABSENT
        and item_is_enrichable(item)
    )
    unsupported_items = tuple(
        item
        for item in exam.items
        if item.answer_key.provenance is DigiExamAnswerKeyProvenance.ABSENT
        and not item_is_enrichable(item)
        and (item.embedded_assets or item.embedded_asset_references)
    )
    assert expected_provider_items
    assert unsupported_items
    assert frozenset(item.item_id for item in plan.unkeyed_items) == expected_provider_items

    actor = await _actor(db_session)
    jobs = PostgreSQLConversionHubJobRepository(db_session)
    enrichment_jobs = PostgreSQLExamAnswerKeyEnrichmentJobRepository(db_session)
    overlays = PostgreSQLExamAnswerKeyProposedOverlayRepository(db_session)
    sessions = PostgreSQLExamConverterCorrectionSessionRepository(db_session)
    leases = PostgreSQLAnswerKeyTokenLeaseRepository(
        db_session,
        daily_token_limit=10_000_000,
    )
    uow = SQLAlchemyUnitOfWork(db_session)
    clock = UTCClock()
    ids = UUID4Generator()
    artifacts = FilesystemExamConversionArtifactStore(artifacts_root=tmp_path)
    producer = InProcessExamConversionProducer(
        qti_writer=ExamNetQtiPackageWriter(),
        pdf_renderer=WeasyPrintExamNetPdfRenderer(),
    )
    provider = RealRequestProviderBoundary(expected_item_ids=expected_provider_items)

    submitted = await CreateExamConverterConversionJobsHandler(
        jobs=jobs,
        submission_lookup=jobs,
        producer=producer,
        artifacts=artifacts,
        enrichment_jobs=enrichment_jobs,
        enrichment_enabled=True,
        uow=uow,
        clock=clock,
        id_generator=ids,
    ).handle(
        actor=actor,
        upload=upload,
        overlay_bytes=None,
        correlation_id="real-dxe-integration",
        idempotency_key=f"real-dxe-{uuid4()}",
    )
    assert submitted.status.value == "submitted"

    processor = ProcessExamAnswerKeyEnrichmentJobHandler(
        enrichment_jobs=enrichment_jobs,
        conversion_jobs=jobs,
        leases=leases,
        proposed_overlays=overlays,
        provider=provider,
        provider_selector=FixedRouteAnswerKeyProviderSelector(route=provider_route()),
        producer=producer,
        artifacts=artifacts,
        uow=uow,
        clock=clock,
        id_generator=ids,
    )
    worker_container = make_async_container(
        WorkerProvider(handler=processor, jobs=enrichment_jobs, uow=uow)
    )
    try:
        processed = await process_next_answer_key_enrichment_job(
            container=worker_container,
            worker_id="integration-worker",
            now=clock.now(),
            lease_ttl=timedelta(minutes=15),
            clock=clock,
        )
    finally:
        await worker_container.close()
    assert processed
    enrichment_job_id = await db_session.scalar(
        select(ExamAnswerKeyEnrichmentJobModel.id).where(
            ExamAnswerKeyEnrichmentJobModel.conversion_job_id == submitted.job_id
        )
    )
    assert enrichment_job_id is not None
    finished = await enrichment_jobs.get_by_id(job_id=enrichment_job_id)
    assert finished is not None
    assert finished.source_dxe == source_bytes
    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED
    assert frozenset(request.item_id for request in provider.requests) == expected_provider_items

    lease_item_ids = frozenset(
        await db_session.scalars(select(ExamAnswerKeyTokenLeaseModel.item_id))
    )
    assert lease_item_ids == expected_provider_items
    proposed = await overlays.get_by_conversion_job_id(conversion_job_id=submitted.job_id)
    assert proposed is not None
    raw_proposed_items = proposed.overlay_json["items"]
    assert isinstance(raw_proposed_items, list)
    proposed_item_ids = frozenset(
        str(item["item_id"]) for item in raw_proposed_items if isinstance(item, dict)
    )
    assert proposed_item_ids == expected_provider_items

    product = ExamConverterProductHandler(
        jobs=jobs,
        sessions=sessions,
        proposals=overlays,
        producer=producer,
        artifacts=artifacts,
        uow=uow,
    )
    initial = await product.result(actor=actor, job_id=submitted.job_id)
    assert initial.status == "succeeded"
    assert initial.bundle_status == "needs_review"
    assert initial.manual_follow_up_required
    review_rows = _review_rows(
        artifacts.read_named_artifact(
            job_id=submitted.job_id,
            artifact_key="answer_key_review_state_report",
        ).content
    )
    assert all(
        review_rows[item_id]["review_state"] == "review_required"
        for item_id in expected_provider_items
    )
    assert all(
        review_rows[item.item_id]["review_state"] == "validation_required"
        for item in unsupported_items
    )
    completion_rows = _review_rows(
        artifacts.read_named_artifact(
            job_id=submitted.job_id,
            artifact_key="answer_key_completion_report",
        ).content
    )
    assert all(
        completion_rows[item.item_id]["backend_failure_code"] == _PARTIAL_FAILURE_CODE
        for item in unsupported_items
    )

    source_state = await product.source_state(actor=actor, job_id=submitted.job_id)
    binding = ExamConverterCorrectionSourceBinding.model_validate(source_state["source_binding"])
    corrections = ReplaceExamConverterCorrectionIntentsHandler(
        jobs=jobs,
        sessions=sessions,
        uow=uow,
        id_generator=ids,
    )
    accepted_item = next(item for item in exam.items if item.item_id in expected_provider_items)
    await corrections.handle(
        actor=actor,
        job_id=submitted.job_id,
        request=ReplaceExamConverterCorrectionIntentsRequest(
            expected_session_version=0,
            intents=[
                _accepted_intent(
                    item=accepted_item,
                    row=completion_rows[accepted_item.item_id],
                    binding=binding,
                )
            ],
        ),
    )
    partial_replay = await product.replay(actor=actor, job_id=submitted.job_id)
    partial_readiness = partial_replay["readiness"]
    assert isinstance(partial_readiness, dict)
    assert partial_readiness["review_required"] is True
    partial_rows = _review_rows(
        artifacts.read_named_artifact(
            job_id=submitted.job_id,
            artifact_key="answer_key_review_state_report",
        ).content
    )
    assert partial_rows[accepted_item.item_id]["review_state"] == "review_complete"
    assert all(
        partial_rows[item.item_id]["review_state"] == "validation_required"
        for item in unsupported_items
    )

    remaining_provider_items = tuple(
        item
        for item in exam.items
        if item.item_id in expected_provider_items and item.item_id != accepted_item.item_id
    )
    await corrections.handle(
        actor=actor,
        job_id=submitted.job_id,
        request=ReplaceExamConverterCorrectionIntentsRequest(
            expected_session_version=1,
            intents=[
                *(
                    _accepted_intent(
                        item=item,
                        row=completion_rows[item.item_id],
                        binding=binding,
                    )
                    for item in remaining_provider_items
                ),
                *(_manual_intent(item=item, binding=binding) for item in unsupported_items),
            ],
        ),
    )
    replayed_manifest = await product.replay(actor=actor, job_id=submitted.job_id)
    readiness = replayed_manifest["readiness"]
    assert isinstance(readiness, dict)
    assert readiness["review_required"] is False
    replayed_review_rows = _review_rows(
        artifacts.read_named_artifact(
            job_id=submitted.job_id,
            artifact_key="answer_key_review_state_report",
        ).content
    )
    assert all(
        replayed_review_rows[item_id]["review_state"] == "review_complete"
        for item_id in expected_provider_items
    )
    assert all(
        replayed_review_rows[item.item_id]["review_state"] == "teacher_modified"
        for item in unsupported_items
    )
    assert artifacts.read_named_artifact(
        job_id=submitted.job_id,
        artifact_key="qti_package",
    ).content
    assert artifacts.read_named_artifact(
        job_id=submitted.job_id,
        artifact_key="examnet_pdf",
    ).content.startswith(b"%PDF")
