"""Skriptoteket-native product surfaces for authenticated Exam Converter jobs."""

from __future__ import annotations

import json
from uuid import UUID

from pydantic import BaseModel, ConfigDict, JsonValue

from skriptoteket.application.curated_apps.conversion_hub import (
    ConversionHubJob,
    ConversionHubOutputFormatV2,
    ConversionHubSourceFormatV2,
)
from skriptoteket.application.curated_apps.conversion_hub_saved_artifacts import (
    SaveConversionHubSirConvertArtifactResult,
)
from skriptoteket.application.curated_apps.document_converter import DocumentConverterStoredArtifact
from skriptoteket.application.curated_apps.exam_conversion import (
    ExamConversionNamedArtifact,
    ExamConversionStoredArtifact,
    is_local_exam_conversion_job,
)
from skriptoteket.application.curated_apps.exam_conversion_correction_source import (
    build_correction_source_state,
    sha256_digest,
)
from skriptoteket.application.curated_apps.exam_conversion_producers import (
    apply_exam_overlay,
    source_exam_digests,
)
from skriptoteket.application.curated_apps.exam_conversion_review_artifacts import (
    build_artifact_manifest,
    build_review_named_artifacts,
)
from skriptoteket.application.curated_apps.handlers.conversion_hub_jobs import ConversionHubUpload
from skriptoteket.application.curated_apps.handlers.document_converter_vault_saves import (
    DocumentConverterVaultSaveService,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_contracts import (
    DigiExamAnswerKeyProvenance,
    DigiExamItemType,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_ingestion_overlay_contracts import (
    DigiExamIngestionOverlay,
    DigiExamIngestionOverlayItem,
    DigiExamOverlayChoiceItemPatch,
    DigiExamOverlayChoiceManualAnswerKey,
    DigiExamOverlayGapAnswer,
    DigiExamOverlayGapFillItemPatch,
    DigiExamOverlayGapFillManualAnswerKey,
    DigiExamOverlayGenericItemPatch,
    DigiExamOverlayPointCorrection,
    DigiExamOverlaySourceBinding,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_ir_contracts import (
    DIGIEXAM_IR_SCHEMA_VERSION,
    DigiExamIntermediateExam,
    DigiExamIrItem,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_source_fingerprints import (
    source_item_fingerprint,
)
from skriptoteket.domain.curated_apps.exam_converter_correction_sessions import (
    SourceBoundCorrectionIntent,
)
from skriptoteket.domain.errors import DomainError, ErrorCode, not_found, validation_error
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.conversion_hub import ConversionHubJobRepositoryProtocol
from skriptoteket.protocols.exam_answer_key import ExamAnswerKeyProposedOverlayRepositoryProtocol
from skriptoteket.protocols.exam_conversion import (
    ExamConversionArtifactStoreProtocol,
    InProcessExamConverterProtocol,
)
from skriptoteket.protocols.exam_converter_correction_sessions import (
    ExamConverterReplayCorrectionSessionRepositoryProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class ExamConverterProductResult(BaseModel):
    """Native terminal result consumed by the authenticated SPA."""

    model_config = ConfigDict(extra="forbid")

    job_id: UUID
    status: str
    error: str | None
    bundle_status: str | None
    artifact_count: int
    manual_follow_up_required: bool
    warning_count: int


class ExamConverterProductHandler:
    """Read and replay locally owned Exam Converter product state."""

    def __init__(
        self,
        *,
        jobs: ConversionHubJobRepositoryProtocol,
        sessions: ExamConverterReplayCorrectionSessionRepositoryProtocol,
        proposals: ExamAnswerKeyProposedOverlayRepositoryProtocol,
        producer: InProcessExamConverterProtocol,
        artifacts: ExamConversionArtifactStoreProtocol,
        uow: UnitOfWorkProtocol,
    ) -> None:
        self._jobs = jobs
        self._sessions = sessions
        self._proposals = proposals
        self._producer = producer
        self._artifacts = artifacts
        self._uow = uow

    async def result(self, *, actor: User, job_id: UUID) -> ExamConverterProductResult:
        """Return the local terminal projection without an upstream request."""

        job = await self._owned_local_job(actor=actor, job_id=job_id)
        if job.status.value != "succeeded":
            return ExamConverterProductResult(
                job_id=job.id,
                status=job.status.value,
                error=job.error_message,
                bundle_status=None,
                artifact_count=0,
                manual_follow_up_required=False,
                warning_count=0,
            )
        artifact = self._artifacts.read_artifact(job_id=job.id)
        manifest = build_artifact_manifest(
            job_id=job.id,
            source_filename=artifact.source_filename,
            source_content=artifact.source_content,
            artifacts=artifact.named_artifacts,
        )
        manual = manifest["manual_follow_up"]
        required = isinstance(manual, dict) and bool(manual.get("required"))
        return ExamConverterProductResult(
            job_id=job.id,
            status=job.status.value,
            error=job.error_message,
            bundle_status=str(manifest["bundle_status"]),
            artifact_count=len(artifact.named_artifacts),
            manual_follow_up_required=required,
            warning_count=0,
        )

    async def manifest(self, *, actor: User, job_id: UUID) -> dict[str, JsonValue]:
        """Return the named artifact and readiness manifest."""

        await self._owned_local_job(actor=actor, job_id=job_id)
        artifact = self._artifacts.read_artifact(job_id=job_id)
        return build_artifact_manifest(
            job_id=job_id,
            source_filename=artifact.source_filename,
            source_content=artifact.source_content,
            artifacts=artifact.named_artifacts,
        )

    async def named_artifact(
        self,
        *,
        actor: User,
        job_id: UUID,
        artifact_key: str,
    ) -> ExamConversionNamedArtifact:
        """Return one owner-scoped named artifact."""

        await self._owned_local_job(actor=actor, job_id=job_id)
        return self._artifacts.read_named_artifact(job_id=job_id, artifact_key=artifact_key)

    async def source_state(self, *, actor: User, job_id: UUID) -> dict[str, JsonValue]:
        """Issue source-owned correction state directly from the stored upload."""

        await self._owned_local_job(actor=actor, job_id=job_id)
        artifact = self._artifacts.read_artifact(job_id=job_id)
        exam = _parse_stored_source(artifact)
        state = build_correction_source_state(exam)
        state_bytes = _json_bytes(state)
        state_sha256 = sha256_digest(state_bytes)
        state["source_state_sha256"] = state_sha256
        binding: dict[str, JsonValue] = {
            "source_authoring_schema_version": "exam_authoring_ir_v1",
            "source_bundle_id": str(job_id),
            "source_file_sha256": sha256_digest(artifact.source_content),
            "source_state_sha256": state_sha256,
            "source_state_signature": f"local-{state_sha256}",
        }
        return {
            "schema_version": "exam_authoring_correction_source_state_issue_result_v1",
            "source_binding": binding,
            "source_authoring_state": state,
        }

    async def replay(self, *, actor: User, job_id: UUID) -> dict[str, JsonValue]:
        """Regenerate local artifacts from the durable correction current set."""

        await self._owned_local_job(actor=actor, job_id=job_id)
        stored = self._artifacts.read_artifact(job_id=job_id)
        exam = _parse_stored_source(stored)
        async with self._uow:
            session = await self._sessions.get_by_owner_and_job(
                owner_user_id=actor.id,
                conversion_hub_job_id=job_id,
            )
            proposal = await self._proposals.get_by_conversion_job_id(conversion_job_id=job_id)
        proposal_overlay = (
            DigiExamIngestionOverlay.model_validate(proposal.overlay_json) if proposal else None
        )
        correction_version = session.session_version if session is not None else 0
        intents = session.active_replay_intents() if session else ()
        overlay, teacher_key_item_ids = _replay_overlay(
            exam=exam,
            source_file_bytes=stored.source_content,
            proposal_overlay=proposal_overlay,
            intents=intents,
        )
        upload = ConversionHubUpload(
            filename=stored.source_filename,
            content_type="application/octet-stream",
            file_bytes=stored.source_content,
        )
        overlay_bytes = _json_bytes(overlay.model_dump(mode="json")) if overlay else None
        suppressed_item_ids = frozenset(
            intent.item_id for intent in intents if intent.kind.value == "candidate_suppression"
        )
        if suppressed_item_ids:
            effective_exam, effective_report, _ = apply_exam_overlay(
                exam=exam,
                upload=upload,
                overlay_bytes=overlay_bytes,
                overlay_key_provenance=(
                    DigiExamAnswerKeyProvenance.MACHINE_PROPOSED_KEY
                    if proposal_overlay is not None
                    else DigiExamAnswerKeyProvenance.MANUAL_TEACHER_KEY
                ),
                teacher_answer_key_item_ids=teacher_key_item_ids,
            )
            artifact = stored.model_copy(
                update={
                    "named_artifacts": build_review_named_artifacts(
                        job_id=job_id,
                        source_exam=exam,
                        effective_exam=effective_exam,
                        effective_report=effective_report,
                        proposal_overlay=_without_items(proposal_overlay, suppressed_item_ids),
                        proposal_provider_profile_id=(
                            proposal.provider_profile_id if proposal else None
                        ),
                        proposal_model=proposal.model if proposal else None,
                        qti_package_bytes=_named_content(stored, "qti_package"),
                        pdf_bytes=_named_content(stored, "examnet_pdf"),
                        validation_report_bytes=_named_content(stored, "qti_validation_report"),
                        correction_intents=intents,
                    )
                }
            )
        else:
            artifact = await self._producer.convert(
                job_id=job_id,
                upload=upload,
                overlay_bytes=overlay_bytes,
                proposal_overlay_bytes=(
                    _json_bytes(proposal_overlay.model_dump(mode="json"))
                    if proposal_overlay
                    else None
                ),
                proposal_provider_profile_id=proposal.provider_profile_id if proposal else None,
                proposal_model=proposal.model if proposal else None,
                teacher_answer_key_item_ids=teacher_key_item_ids,
                correction_intents=intents,
                correlation_id=None,
                overlay_key_provenance=(
                    DigiExamAnswerKeyProvenance.MACHINE_PROPOSED_KEY
                    if proposal_overlay is not None
                    else DigiExamAnswerKeyProvenance.MANUAL_TEACHER_KEY
                ),
            )
        async with self._uow:
            current_session = await self._sessions.get_by_owner_and_job_for_update(
                owner_user_id=actor.id,
                conversion_hub_job_id=job_id,
            )
            current_version = current_session.session_version if current_session is not None else 0
            if current_version != correction_version:
                raise DomainError(
                    code=ErrorCode.CONFLICT,
                    message="Corrections changed while artifacts were being regenerated.",
                    details={
                        "expected_session_version": correction_version,
                        "current_session_version": current_version,
                    },
                )
            self._artifacts.store_artifact(job_id=job_id, artifact=artifact)
        return await self.manifest(actor=actor, job_id=job_id)

    async def _owned_local_job(self, *, actor: User, job_id: UUID) -> ConversionHubJob:
        async with self._uow:
            job = await self._jobs.get_by_id(job_id=job_id)
        is_exam_job = (
            job is not None
            and job.source_format is ConversionHubSourceFormatV2.DIGIEXAM_DXE
            and job.output_format is ConversionHubOutputFormatV2.EXAMNET_BUNDLE
        )
        is_native_job = job is not None and (
            job.upstream_job_id is None or is_local_exam_conversion_job(job)
        )
        if job is None or job.owner_user_id != actor.id or not is_exam_job or not is_native_job:
            raise not_found("ConversionHubJob", str(job_id))
        return job


class SaveExamConverterLocalArtifactHandler:
    """Save one owner-authorized local artifact without a browser re-upload."""

    def __init__(
        self,
        *,
        product: ExamConverterProductHandler,
        vault_saves: DocumentConverterVaultSaveService,
    ) -> None:
        self._product = product
        self._vault_saves = vault_saves

    async def handle(
        self,
        *,
        actor: User,
        job_id: UUID,
        artifact_key: str,
    ) -> SaveConversionHubSirConvertArtifactResult:
        artifact = await self._product.named_artifact(
            actor=actor, job_id=job_id, artifact_key=artifact_key
        )
        source_artifact_id = f"documents.conversion_hub:exam-converter:{job_id}:{artifact_key}"
        saved = await self._vault_saves.save(
            actor=actor,
            artifact=DocumentConverterStoredArtifact(
                filename=artifact.filename,
                content_type=artifact.content_type,
                content=artifact.content,
            ),
            source_artifact_id=source_artifact_id,
        )
        return SaveConversionHubSirConvertArtifactResult(
            vault_artifact=saved,
            source_artifact_id=source_artifact_id,
        )


def _parse_stored_source(stored: ExamConversionStoredArtifact) -> DigiExamIntermediateExam:
    from skriptoteket.application.curated_apps.exam_conversion_producers import parse_source_exam

    return parse_source_exam(
        upload=ConversionHubUpload(
            filename=stored.source_filename,
            content_type="application/octet-stream",
            file_bytes=stored.source_content,
        )
    )


def _without_items(
    overlay: DigiExamIngestionOverlay | None,
    item_ids: frozenset[str],
) -> DigiExamIngestionOverlay | None:
    if overlay is None:
        return None
    return overlay.model_copy(
        update={"items": tuple(item for item in overlay.items if item.item_id not in item_ids)}
    )


def _named_content(stored: ExamConversionStoredArtifact, artifact_key: str) -> bytes:
    for artifact in stored.named_artifacts:
        if artifact.artifact_key == artifact_key:
            return artifact.content
    raise not_found("ExamConversionNamedArtifact", artifact_key)


def _replay_overlay(
    *,
    exam: DigiExamIntermediateExam,
    source_file_bytes: bytes,
    proposal_overlay: DigiExamIngestionOverlay | None,
    intents: tuple[SourceBoundCorrectionIntent, ...],
) -> tuple[DigiExamIngestionOverlay | None, frozenset[str]]:
    items_by_id = {item.item_id: item for item in exam.items}
    entries = {
        item.item_id: item.model_copy()
        for item in (proposal_overlay.items if proposal_overlay is not None else ())
    }
    teacher_key_item_ids: set[str] = set()
    for intent in intents:
        source_item = items_by_id.get(intent.item_id)
        if (
            source_item is None
            or source_item_fingerprint(source_item) != intent.source_item_fingerprint
        ):
            raise validation_error("Correction intent no longer matches the current exam source.")
        current = entries.get(intent.item_id) or DigiExamIngestionOverlayItem(
            item_id=source_item.item_id,
            sequence=source_item.sequence,
            item_type=source_item.item_type,
            source_item_fingerprint=intent.source_item_fingerprint,
        )
        if intent.kind.value == "candidate_suppression":
            _validate_candidate_lineage(intent)
            entries.pop(intent.item_id, None)
            continue
        if intent.kind.value == "point_correction":
            max_score = intent.payload.get("max_score")
            if not isinstance(max_score, int) or isinstance(max_score, bool):
                raise validation_error("Point correction payload is invalid.")
            current = current.model_copy(
                update={
                    "point_correction": DigiExamOverlayPointCorrection(
                        kind="item_points", max_score=max_score
                    )
                }
            )
        elif intent.kind.value == "manual_choice_answer_key":
            choice_ids = intent.payload.get("correct_choice_ids")
            if not isinstance(choice_ids, list):
                raise validation_error("Choice correction payload is invalid.")
            current = current.model_copy(
                update={
                    "manual_answer_key": DigiExamOverlayChoiceManualAnswerKey(
                        kind="choice",
                        correct_alternative_ids=tuple(
                            _choice_source_id(value) for value in choice_ids
                        ),
                    )
                }
            )
            teacher_key_item_ids.add(intent.item_id)
        elif intent.kind.value == "manual_gap_open_cloze_answer_key":
            gap_answers = intent.payload.get("gap_answers")
            if not isinstance(gap_answers, list):
                raise validation_error("Gap correction payload is invalid.")
            current = current.model_copy(
                update={
                    "manual_answer_key": DigiExamOverlayGapFillManualAnswerKey(
                        kind="gap_fill",
                        gap_answers=tuple(
                            DigiExamOverlayGapAnswer.model_validate(answer)
                            for answer in gap_answers
                        ),
                    )
                }
            )
            teacher_key_item_ids.add(intent.item_id)
        elif intent.kind.value == "item_text_patch":
            current = current.model_copy(
                update={"effective_item_patch": _text_patch(source_item, intent.payload)}
            )
        entries[intent.item_id] = current
    if not entries:
        return None, frozenset(teacher_key_item_ids)
    source_file_sha256, source_ir_sha256 = source_exam_digests(
        file_bytes=source_file_bytes,
        exam=exam,
    )
    return (
        DigiExamIngestionOverlay(
            schema_version="digiexam_ingestion_overlay_v2",
            source_binding=DigiExamOverlaySourceBinding(
                source_file_sha256=source_file_sha256,
                source_ir_schema_version=DIGIEXAM_IR_SCHEMA_VERSION,
                source_ir_sha256=source_ir_sha256,
            ),
            items=tuple(entries.values()),
        ),
        frozenset(teacher_key_item_ids),
    )


def _text_patch(
    item: DigiExamIrItem, payload: dict[str, JsonValue]
) -> (
    DigiExamOverlayChoiceItemPatch
    | DigiExamOverlayGapFillItemPatch
    | DigiExamOverlayGenericItemPatch
):
    patches = payload.get("patches")
    if not isinstance(patches, list) or len(patches) != 1 or not isinstance(patches[0], dict):
        raise validation_error("Text correction payload is invalid.")
    patch = patches[0]
    field = patch.get("field")
    value = patch.get("value")
    if not isinstance(field, str) or not isinstance(value, str):
        raise validation_error("Text correction payload is invalid.")
    kind = "gap_fill" if item.item_type is DigiExamItemType.GAP_FILL else "generic"
    if item.item_type in {
        DigiExamItemType.SINGLE_CHOICE,
        DigiExamItemType.MULTIPLE_CHOICE,
        DigiExamItemType.MULTIPLE_RESPONSE,
    }:
        kind = "choice"
    update: dict[str, JsonValue] = {"kind": kind}
    if field == "item_title":
        update["title"] = value
    elif field == "prompt_html":
        update["prompt_html"] = value
    elif field == "prompt_lines":
        update["prompt_lines"] = [value]
    else:
        raise validation_error("Unsupported text correction field.")
    if item.item_type is DigiExamItemType.GAP_FILL:
        return DigiExamOverlayGapFillItemPatch.model_validate(update)
    if kind == "choice":
        return DigiExamOverlayChoiceItemPatch.model_validate(update)
    return DigiExamOverlayGenericItemPatch.model_validate(update)


def _choice_source_id(value: JsonValue) -> int:
    if not isinstance(value, str) or not value.startswith("choice-"):
        raise validation_error("Choice correction references an unknown source choice.")
    try:
        return int(value.removeprefix("choice-"))
    except ValueError as exc:
        raise validation_error("Choice correction references an unknown source choice.") from exc


def _validate_candidate_lineage(intent: SourceBoundCorrectionIntent) -> None:
    lineage = intent.payload.get("candidate_lineage")
    if not isinstance(lineage, dict):
        raise validation_error("Candidate suppression lineage is invalid.")
    candidate_id = lineage.get("candidate_id")
    candidate_digest = lineage.get("candidate_payload_digest")
    if (
        candidate_id != intent.target.candidate_lineage_id
        or candidate_digest != intent.target.candidate_payload_digest
    ):
        raise validation_error("Candidate suppression lineage no longer matches its target.")


def _json_bytes(value: JsonValue) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n").encode()
