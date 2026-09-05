from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel

from skriptoteket.application.curated_apps.conversion_hub import (
    ConversionHubJob,
    ConversionHubJobStatus,
    ConversionHubOutputFormatV2,
    ConversionHubSourceFormatV2,
)
from skriptoteket.application.curated_apps.exam_conversion import ExamConversionStoredArtifact
from skriptoteket.application.curated_apps.exam_conversion_producers import (
    InProcessExamConversionProducer,
)
from skriptoteket.application.curated_apps.handlers.conversion_hub_jobs import ConversionHubUpload
from skriptoteket.application.curated_apps.handlers.document_converter_vault_saves import (
    DocumentConverterVaultSaveService,
)
from skriptoteket.application.curated_apps.handlers.exam_converter_product import (
    ExamConverterProductHandler,
    SaveExamConverterLocalArtifactHandler,
)
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.exam_converter_correction_sessions import (
    ExamConverterCorrectionIntentKind,
    ExamConverterCorrectionSession,
    ExamConverterCorrectionSourceBinding,
    ExamConverterCorrectionTarget,
    SourceBoundCorrectionIntent,
)
from skriptoteket.domain.identity.models import AuthProvider, Role, User
from skriptoteket.domain.scripting.vault import VaultUsage
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_conversion_artifacts import (
    FilesystemExamConversionArtifactStore,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_pdf_renderer import (
    WeasyPrintExamNetPdfRenderer,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_qti_writer import (
    ExamNetQtiPackageWriter,
)
from tests.fixtures.time_fixtures import FixedClock
from tests.unit.application.curated_apps.handlers.test_conversion_hub_jobs import (
    SequenceIdGenerator,
)
from tests.unit.application.curated_apps.handlers.test_document_converter_artifact_saves import (
    InMemoryVaultFileRepository,
    InMemoryVaultStorage,
    InMemoryVaultUsageRepository,
)


class FakeUow:
    async def __aenter__(self) -> FakeUow:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


def test_artifact_store_deletes_expired_job_directory(tmp_path: Path) -> None:
    job_id = uuid4()
    artifacts = FilesystemExamConversionArtifactStore(artifacts_root=tmp_path)
    artifacts.store_artifact(
        job_id=job_id,
        artifact=ExamConversionStoredArtifact(
            filename="bundle.zip",
            content_type="application/zip",
            content=b"bundle",
            source_filename="exam.dxe",
            source_content=b"dxe",
        ),
    )

    artifacts.delete_artifact(job_id=job_id)

    assert not (tmp_path / "exam-conversion" / str(job_id)).exists()


class JobRepository:
    def __init__(self, job: ConversionHubJob) -> None:
        self.job = job

    async def create(self, *, job: ConversionHubJob) -> ConversionHubJob:
        self.job = job
        return job

    async def get_by_id(self, *, job_id: UUID) -> ConversionHubJob | None:
        return self.job if self.job.id == job_id else None

    async def get_by_upstream_job_id(self, *, upstream_job_id: str) -> ConversionHubJob | None:
        return self.job if self.job.upstream_job_id == upstream_job_id else None

    async def update(self, *, job: ConversionHubJob) -> ConversionHubJob:
        self.job = job
        return job


class SessionRepository:
    def __init__(self) -> None:
        self.session: ExamConverterCorrectionSession | None = None
        self.locked_jobs: list[tuple[UUID, UUID]] = []

    async def lock_owned_job(self, *, owner_user_id: UUID, conversion_hub_job_id: UUID) -> None:
        self.locked_jobs.append((owner_user_id, conversion_hub_job_id))

    async def get_by_owner_and_job(
        self, *, owner_user_id: UUID, conversion_hub_job_id: UUID
    ) -> ExamConverterCorrectionSession | None:
        if self.session is None:
            return None
        if (
            self.session.owner_user_id == owner_user_id
            and self.session.conversion_hub_job_id == conversion_hub_job_id
        ):
            return self.session
        return None

    async def get_by_owner_and_job_for_update(
        self, *, owner_user_id: UUID, conversion_hub_job_id: UUID
    ) -> ExamConverterCorrectionSession | None:
        return await self.get_by_owner_and_job(
            owner_user_id=owner_user_id,
            conversion_hub_job_id=conversion_hub_job_id,
        )

    async def save(
        self, *, session: ExamConverterCorrectionSession, expected_session_version: int
    ) -> ExamConverterCorrectionSession:
        del expected_session_version
        self.session = session
        return session


class ProposalRepository:
    async def create(self, *, proposed_overlay):
        return proposed_overlay

    async def get_by_conversion_job_id(self, *, conversion_job_id: UUID):
        del conversion_job_id
        return None


class SourceStateItem(BaseModel):
    item_id: str
    item_type: str
    sequence: int
    source_item_fingerprint: str


class SourceAuthoringState(BaseModel):
    items: list[SourceStateItem]


class SourceStateResult(BaseModel):
    source_binding: ExamConverterCorrectionSourceBinding
    source_authoring_state: SourceAuthoringState


def _upload(*, filename: str = "exam.dxe") -> ConversionHubUpload:
    payload = {
        "exams": [
            {
                "questions": [
                    {
                        "id": 1,
                        "title": "Single choice",
                        "about": "",
                        "bodyHTML": "<p>Choose.</p>",
                        "images": [],
                        "maxScore": 2,
                        "type": 1,
                        "alternatives": [
                            {"id": 1, "title": "Alpha", "about": "", "right": False},
                            {"id": 2, "title": "Beta", "about": "", "right": True},
                        ],
                    }
                ]
            }
        ]
    }
    return ConversionHubUpload(
        filename=filename,
        content_type="application/octet-stream",
        file_bytes=json.dumps(payload).encode(),
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_provider_failure_still_produces_typed_review_artifacts() -> None:
    upload = _upload()
    payload = json.loads(upload.file_bytes)
    payload["exams"][0]["questions"][0]["alternatives"][1]["right"] = False
    unkeyed_upload = ConversionHubUpload(
        filename=upload.filename,
        content_type=upload.content_type,
        file_bytes=json.dumps(payload).encode("utf-8"),
    )
    producer = InProcessExamConversionProducer(
        qti_writer=ExamNetQtiPackageWriter(),
        pdf_renderer=WeasyPrintExamNetPdfRenderer(),
    )

    artifact = await producer.convert(
        job_id=uuid4(),
        upload=unkeyed_upload,
        overlay_bytes=None,
        correlation_id=None,
        enrichment_failure_code="provider_timeout",
        retry_identity="retry-native-2",
    )

    completion_artifact = next(
        named
        for named in artifact.named_artifacts
        if named.artifact_key == "answer_key_completion_report"
    )
    completion = json.loads(completion_artifact.content)
    item = completion["items"][0]
    assert item["decision_state"] == "manual_follow_up_required"
    assert item["backend_status"] == "failed"
    assert item["backend_failure_code"] == "provider_timeout"
    assert item["retry_identity"] == "retry-native-2"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_replay_projects_durable_point_correction_into_local_artifacts(
    tmp_path: Path,
) -> None:
    job_id = uuid4()
    now = datetime(2026, 8, 30, tzinfo=UTC)
    actor = User(
        id=uuid4(),
        email="teacher@example.test",
        role=Role.USER,
        auth_provider=AuthProvider.HULEEDU,
        created_at=now,
        updated_at=now,
    )
    job = ConversionHubJob(
        id=job_id,
        owner_user_id=actor.id,
        input_filename="exam.dxe",
        source_format=ConversionHubSourceFormatV2.DIGIEXAM_DXE,
        output_format=ConversionHubOutputFormatV2.EXAMNET_BUNDLE,
        upstream_job_id=None,
        status=ConversionHubJobStatus.SUCCEEDED,
        created_at=now,
        updated_at=now,
    )
    producer = InProcessExamConversionProducer(
        qti_writer=ExamNetQtiPackageWriter(),
        pdf_renderer=WeasyPrintExamNetPdfRenderer(),
    )
    artifacts = FilesystemExamConversionArtifactStore(artifacts_root=tmp_path)
    upload = _upload(filename="Samhällskunskap.slutprov.DXE")
    artifacts.store_artifact(
        job_id=job_id,
        artifact=await producer.convert(
            job_id=job_id,
            upload=upload,
            overlay_bytes=None,
            correlation_id=None,
        ),
    )
    sessions = SessionRepository()
    handler = ExamConverterProductHandler(
        jobs=JobRepository(job),
        sessions=sessions,
        proposals=ProposalRepository(),
        producer=producer,
        artifacts=artifacts,
        uow=FakeUow(),
    )
    first_pass_manifest = await handler.manifest(actor=actor, job_id=job_id)
    first_pass_entries = first_pass_manifest["artifacts"]
    assert isinstance(first_pass_entries, list)
    first_pass_filenames = {
        str(entry["artifact_key"]): str(entry["filename"])
        for entry in first_pass_entries
        if isinstance(entry, dict)
    }
    assert first_pass_filenames["examnet_pdf"] == ("Samhällskunskap.slutprov - Exam.net.pdf")
    assert first_pass_filenames["qti_package"] == "Samhällskunskap.slutprov - QTI.zip"

    source_state = await handler.source_state(actor=actor, job_id=job_id)
    issued = SourceStateResult.model_validate(source_state)
    binding = issued.source_binding
    item = issued.source_authoring_state.items[0]
    sessions.session = ExamConverterCorrectionSession(
        id=uuid4(),
        owner_user_id=actor.id,
        conversion_hub_job_id=job_id,
        source_binding=binding,
        session_version=1,
        active_intents=(
            SourceBoundCorrectionIntent(
                intent_id=uuid4(),
                entry_id="corr-points-item-001",
                source_binding=binding,
                item_id=item.item_id,
                sequence=item.sequence,
                item_type=item.item_type,
                source_item_fingerprint=item.source_item_fingerprint,
                kind=ExamConverterCorrectionIntentKind.POINT_CORRECTION,
                target=ExamConverterCorrectionTarget(),
                payload={"max_score": 3},
            ),
            SourceBoundCorrectionIntent(
                intent_id=uuid4(),
                entry_id="corr-title-item-001",
                source_binding=binding,
                item_id=item.item_id,
                sequence=item.sequence,
                item_type=item.item_type,
                source_item_fingerprint=item.source_item_fingerprint,
                kind=ExamConverterCorrectionIntentKind.ITEM_TEXT_PATCH,
                target=ExamConverterCorrectionTarget(text_field="item_title"),
                payload={"patches": [{"field": "item_title", "value": "Teacher title"}]},
            ),
            SourceBoundCorrectionIntent(
                intent_id=uuid4(),
                entry_id="corr-choice-item-001",
                source_binding=binding,
                item_id=item.item_id,
                sequence=item.sequence,
                item_type=item.item_type,
                source_item_fingerprint=item.source_item_fingerprint,
                kind=ExamConverterCorrectionIntentKind.MANUAL_CHOICE_ANSWER_KEY,
                target=ExamConverterCorrectionTarget(interaction_id=f"choice-{item.item_id}"),
                payload={"correct_choice_ids": ["choice-1"]},
            ),
        ),
    )

    manifest = await handler.replay(actor=actor, job_id=job_id)
    effective = artifacts.read_named_artifact(
        job_id=job_id,
        artifact_key="effective_ir_json",
    )
    effective_payload = json.loads(effective.content)
    review_ir = artifacts.read_named_artifact(job_id=job_id, artifact_key="ir_json")
    review_ir_payload = json.loads(review_ir.content)

    replay_entries = manifest["artifacts"]
    assert isinstance(replay_entries, list)
    replay_filenames = {
        str(entry["artifact_key"]): str(entry["filename"])
        for entry in replay_entries
        if isinstance(entry, dict)
    }
    assert manifest["job_id"] == str(job_id)
    assert replay_filenames["examnet_pdf"] == first_pass_filenames["examnet_pdf"]
    assert replay_filenames["qti_package"] == first_pass_filenames["qti_package"]
    assert sessions.locked_jobs == [(actor.id, job_id)]
    assert effective_payload["items"][0]["effective_point_correction"]["effective_max_score"] == 3
    assert review_ir_payload["items"][0]["max_score"] == 3
    assert review_ir_payload["items"][0]["title"] == "Teacher title"
    assert review_ir_payload["items"][0]["answer_key"]["correct_alternative_ids"] == [1]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_max_length_targets_reach_manifest_and_mina_filer_collision(
    tmp_path: Path,
) -> None:
    job_id = uuid4()
    now = datetime(2026, 9, 5, tzinfo=UTC)
    source_filename = f"{'x' * 251}.DXE"
    actor = User(
        id=uuid4(),
        email="teacher@example.test",
        role=Role.USER,
        auth_provider=AuthProvider.HULEEDU,
        created_at=now,
        updated_at=now,
    )
    job = ConversionHubJob(
        id=job_id,
        owner_user_id=actor.id,
        input_filename=source_filename,
        source_format=ConversionHubSourceFormatV2.DIGIEXAM_DXE,
        output_format=ConversionHubOutputFormatV2.EXAMNET_BUNDLE,
        upstream_job_id=None,
        status=ConversionHubJobStatus.SUCCEEDED,
        created_at=now,
        updated_at=now,
    )
    producer = InProcessExamConversionProducer(
        qti_writer=ExamNetQtiPackageWriter(),
        pdf_renderer=WeasyPrintExamNetPdfRenderer(),
    )
    artifacts = FilesystemExamConversionArtifactStore(artifacts_root=tmp_path)
    artifacts.store_artifact(
        job_id=job_id,
        artifact=await producer.convert(
            job_id=job_id,
            upload=_upload(filename=source_filename),
            overlay_bytes=None,
            correlation_id=None,
        ),
    )
    product = ExamConverterProductHandler(
        jobs=JobRepository(job),
        sessions=SessionRepository(),
        proposals=ProposalRepository(),
        producer=producer,
        artifacts=artifacts,
        uow=FakeUow(),
    )
    manifest = await product.manifest(actor=actor, job_id=job_id)
    entries = manifest["artifacts"]
    assert isinstance(entries, list)
    filenames = {
        str(entry["artifact_key"]): str(entry["filename"])
        for entry in entries
        if isinstance(entry, dict)
    }
    assert len(artifacts.read_artifact(job_id=job_id).filename) == 270
    assert len(filenames["examnet_pdf"]) == 255
    assert len(filenames["qti_package"]) == 255

    first_pdf_id = uuid4()
    second_pdf_id = uuid4()
    qti_id = uuid4()
    vault_files = InMemoryVaultFileRepository()
    save = SaveExamConverterLocalArtifactHandler(
        product=product,
        vault_saves=DocumentConverterVaultSaveService(
            vault_files=vault_files,
            vault_usage=InMemoryVaultUsageRepository(
                usage=VaultUsage(user_id=actor.id, bytes_total=0, updated_at=now)
            ),
            vault_storage=InMemoryVaultStorage(),
            uow=FakeUow(),
            clock=FixedClock(now),
            id_generator=SequenceIdGenerator([first_pdf_id, second_pdf_id, qti_id]),
            settings=Settings.model_construct(
                VAULT_MAX_FILE_BYTES=1_000_000,
                VAULT_MAX_TOTAL_BYTES=2_000_000,
            ),
        ),
    )

    first_pdf = await save.handle(actor=actor, job_id=job_id, artifact_key="examnet_pdf")
    second_pdf = await save.handle(actor=actor, job_id=job_id, artifact_key="examnet_pdf")
    qti = await save.handle(actor=actor, job_id=job_id, artifact_key="qti_package")

    assert first_pdf.vault_artifact.name == filenames["examnet_pdf"]
    assert second_pdf.vault_artifact.name == (
        f"{'x' * (255 - len(' - Exam.net (2).pdf'))} - Exam.net (2).pdf"
    )
    assert len(second_pdf.vault_artifact.name) == 255
    assert qti.vault_artifact.name == filenames["qti_package"]
    assert len(qti.vault_artifact.name) == 255
    assert vault_files.files[first_pdf_id].source_artifact_id == (
        f"documents.conversion_hub:exam-converter:{job_id}:examnet_pdf"
    )
    assert vault_files.files[qti_id].source_artifact_id == (
        f"documents.conversion_hub:exam-converter:{job_id}:qti_package"
    )
