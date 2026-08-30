"""Native review, readiness, and artifact projections for Exam Converter jobs."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from uuid import UUID

from pydantic import JsonValue

from skriptoteket.application.curated_apps.exam_conversion import ExamConversionNamedArtifact
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_completion import (
    CHOICE_PROMPT_TEMPLATE_VERSION,
    GAP_FILL_PROMPT_TEMPLATE_VERSION,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_contracts import (
    DigiExamAnswerKeyProvenance,
    DigiExamItemType,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_ingestion_overlay_contracts import (
    DigiExamEffectiveExam,
    DigiExamIngestionOverlay,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_ir_contracts import (
    DigiExamIntermediateExam,
    DigiExamIrItem,
    DigiExamIrManifest,
    build_digiexam_ir_manifest,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_source_fingerprints import (
    source_item_fingerprint,
)
from skriptoteket.domain.curated_apps.exam_converter_correction_sessions import (
    SourceBoundCorrectionIntent,
)

_MACHINE_MARKED = frozenset(
    {
        DigiExamItemType.MULTIPLE_CHOICE,
        DigiExamItemType.SINGLE_CHOICE,
        DigiExamItemType.MULTIPLE_RESPONSE,
        DigiExamItemType.GAP_FILL,
    }
)


def build_review_named_artifacts(
    *,
    job_id: UUID,
    source_exam: DigiExamIntermediateExam,
    effective_exam: DigiExamIntermediateExam,
    effective_report: DigiExamEffectiveExam | None,
    proposal_overlay: DigiExamIngestionOverlay | None,
    proposal_provider_profile_id: str | None,
    proposal_model: str | None,
    qti_package_bytes: bytes,
    pdf_bytes: bytes,
    validation_report_bytes: bytes,
    correction_intents: tuple[SourceBoundCorrectionIntent, ...] = (),
    enrichment_failure_code: str | None = None,
    retry_identity: str | None = None,
) -> tuple[ExamConversionNamedArtifact, ...]:
    """Build the complete local product projection from owned conversion state."""

    source_ir_bytes = _json_bytes(source_exam)
    review_ir_bytes = _json_bytes(effective_exam)
    source_ir_sha256 = _sha256(source_ir_bytes)
    effective_bytes = (
        _json_bytes(effective_report) if effective_report is not None else source_ir_bytes
    )
    effective_sha256 = _sha256(effective_bytes)
    proposal_items = {
        item.item_id: item for item in (proposal_overlay.items if proposal_overlay else ())
    }
    review_state, blocked_item_ids = _review_state(
        source_exam=source_exam,
        effective_exam=effective_exam,
        proposal_item_ids=frozenset(proposal_items),
        correction_intents=correction_intents,
    )
    readiness = _target_readiness(
        job_id=job_id,
        source_ir_sha256=source_ir_sha256,
        effective_exam_sha256=effective_sha256,
        blocked_item_ids=blocked_item_ids,
        source_exam=source_exam,
    )
    artifacts = [
        _named("examnet_pdf", "examnet-import.pdf", "application/pdf", pdf_bytes),
        _named("qti_package", "qti-package.zip", "application/zip", qti_package_bytes),
        _named(
            "qti_validation_report",
            "qti-validation-report.json",
            "application/json",
            validation_report_bytes,
        ),
        _named("ir_json", "digiexam-ir.json", "application/json", review_ir_bytes),
        _named(
            "source_ir_json",
            "digiexam-source-ir.json",
            "application/json",
            source_ir_bytes,
        ),
        _named(
            "migration_manifest",
            "digiexam-ir-manifest.json",
            "application/json",
            _json_bytes(build_digiexam_ir_manifest(source_exam)),
        ),
        _named(
            "target_readiness_report",
            "target-readiness-report.json",
            "application/json",
            _json_bytes(readiness),
        ),
        _named(
            "answer_key_review_state_report",
            "answer-key-review-state.json",
            "application/json",
            _json_bytes(review_state),
        ),
    ]
    if effective_report is not None:
        artifacts.append(
            _named("effective_ir_json", "effective-ir.json", "application/json", effective_bytes)
        )
    completion = _completion_report(
        source_exam=source_exam,
        proposal_overlay=proposal_overlay,
        provider_profile_id=proposal_provider_profile_id,
        model=proposal_model,
        failure_code=enrichment_failure_code,
        retry_identity=retry_identity,
    )
    artifacts.append(
        _named(
            "answer_key_completion_report",
            "answer-key-completion-report.json",
            "application/json",
            _json_bytes(completion),
        )
    )
    return tuple(artifacts)


def build_artifact_manifest(
    *,
    job_id: UUID,
    source_filename: str,
    source_content: bytes,
    artifacts: tuple[ExamConversionNamedArtifact, ...],
) -> dict[str, JsonValue]:
    """Build the browser-facing manifest from stored named artifacts."""

    entries: list[JsonValue] = [
        _artifact_entry(job_id=job_id, artifact=artifact) for artifact in artifacts
    ]
    readiness_bytes = next(
        artifact.content
        for artifact in artifacts
        if artifact.artifact_key == "target_readiness_report"
    )
    readiness = json.loads(readiness_bytes)
    targets = readiness.get("targets", []) if isinstance(readiness, dict) else []
    readiness_rows = [row for row in targets if isinstance(row, dict)]
    exportable_targets: list[JsonValue] = [
        row.get("target")
        for row in readiness_rows
        if row.get("item_id") is None and row.get("export_enabled") is True
    ]
    review_required = any(row.get("export_enabled") is not True for row in readiness_rows)
    review_ir_bytes = next(
        artifact.content for artifact in artifacts if artifact.artifact_key == "ir_json"
    )
    source_ir_bytes = next(
        artifact.content for artifact in artifacts if artifact.artifact_key == "source_ir_json"
    )
    effective = next(
        (
            artifact.content
            for artifact in artifacts
            if artifact.artifact_key == "effective_ir_json"
        ),
        review_ir_bytes,
    )
    return {
        "schema_version": "digiexam_migration_bundle_v3",
        "job_id": str(job_id),
        "source": {
            "filename": source_filename,
            "format": "digiexam_dxe",
            "sha256": _sha256(source_content),
        },
        "bundle_status": "needs_review" if review_required else "complete",
        "artifacts": entries,
        "manual_follow_up": {
            "required": review_required,
            "artifact_key": "target_readiness_report",
            "count": sum(1 for row in readiness_rows if row.get("item_id") is not None),
        },
        "warnings": None,
        "readiness": {
            "artifact_key": "target_readiness_report",
            "exportable_targets": exportable_targets,
            "review_required": review_required,
        },
        "source_binding": {
            "source_ir_schema_version": "digiexam_intermediate_exam_v3",
            "source_ir_sha256": _sha256(source_ir_bytes),
            "effective_exam_schema_version": "digiexam_effective_exam_v2",
            "effective_exam_sha256": _sha256(effective),
        },
    }


def _review_state(
    *,
    source_exam: DigiExamIntermediateExam,
    effective_exam: DigiExamIntermediateExam,
    proposal_item_ids: frozenset[str],
    correction_intents: tuple[SourceBoundCorrectionIntent, ...],
) -> tuple[dict[str, JsonValue], set[str]]:
    effective_by_id = {item.item_id: item for item in effective_exam.items}
    rows: list[JsonValue] = []
    blocked_item_ids: set[str] = set()
    manual_intents = {
        intent.item_id: intent
        for intent in correction_intents
        if intent.kind.value in {"manual_choice_answer_key", "manual_gap_open_cloze_answer_key"}
    }
    for item in source_exam.items:
        effective_item = effective_by_id[item.item_id]
        is_machine = item.item_id in proposal_item_ids
        provenance = effective_item.answer_key.provenance
        if is_machine and provenance is DigiExamAnswerKeyProvenance.MACHINE_PROPOSED_KEY:
            review_state = "review_required"
            origin = "none"
            reasons = ["advisory_candidate_pending"]
            message_key = "exam_converter.answer_key.advisory_pending"
        elif provenance is DigiExamAnswerKeyProvenance.MANUAL_TEACHER_KEY:
            intent = manual_intents.get(item.item_id)
            submission_origin = (
                intent.payload.get("submission_origin") if intent is not None else None
            )
            review_state = "teacher_modified"
            origin = "teacher_authored"
            reasons = ["teacher_answer_key_present"]
            message_key = "exam_converter.answer_key.teacher_answer_key_present"
            provenance_detail = None
            if submission_origin == "accepted_advisory_candidate" and intent is not None:
                review_state = "review_complete"
                origin = "reviewed_advisory"
                reasons = ["reviewed_advisory_accepted"]
                message_key = "exam_converter.answer_key.advisory_accepted"
                provenance_detail = intent.payload.get("candidate_lineage")
            elif submission_origin == "teacher_edited_advisory_candidate" and intent is not None:
                origin = "teacher_edited_advisory"
                reasons = ["teacher_edited_advisory_candidate"]
                message_key = "exam_converter.answer_key.advisory_edited"
                provenance_detail = intent.payload.get("candidate_lineage")
        elif provenance is not DigiExamAnswerKeyProvenance.ABSENT:
            review_state = "review_complete"
            origin = "source_provided"
            reasons = ["source_answer_key_present"]
            message_key = "exam_converter.answer_key.source_present"
        elif item.item_type in _MACHINE_MARKED:
            review_state = "validation_required"
            origin = "none"
            reasons = ["manual_answer_key_required"]
            message_key = "exam_converter.answer_key.manual_required"
        else:
            review_state = "review_complete"
            origin = "none"
            reasons = ["answer_key_not_applicable"]
            message_key = "exam_converter.answer_key.not_applicable"
        if provenance is not DigiExamAnswerKeyProvenance.MANUAL_TEACHER_KEY:
            provenance_detail = None
        if review_state in {"review_required", "validation_required"}:
            blocked_item_ids.add(item.item_id)
        rows.append(
            {
                "item_id": item.item_id,
                "sequence": item.sequence,
                "item_type": item.item_type.value,
                "source_item_fingerprint": source_item_fingerprint(item),
                "review_state": review_state,
                "current_key_origin": origin,
                "reasons": list(reasons),
                "message_key": message_key,
                "choice_ids": [
                    f"choice-{value}" for value in effective_item.answer_key.correct_alternative_ids
                ],
                "choice_interaction_ids": (
                    [f"choice-{item.item_id}"] if item.item_type in _MACHINE_MARKED else []
                ),
                "gap_ids": [
                    answer.guid for answer in effective_item.answer_key.correct_gap_answers
                ],
                "gap_interaction_ids": (
                    [f"gap-{item.item_id}"] if item.item_type is DigiExamItemType.GAP_FILL else []
                ),
                "correction_affordances": _correction_affordances(item),
                "provenance_detail": provenance_detail,
                "replay_artifact_references": [],
            }
        )
    return (
        {"schema_version": "digiexam_answer_key_review_state_v1", "items": rows},
        blocked_item_ids,
    )


def _correction_affordances(item: DigiExamIrItem) -> list[JsonValue]:
    affordances: list[JsonValue] = ["item_text_patch", "point_correction"]
    if item.item_type in {
        DigiExamItemType.MULTIPLE_CHOICE,
        DigiExamItemType.SINGLE_CHOICE,
        DigiExamItemType.MULTIPLE_RESPONSE,
    }:
        affordances.append("manual_choice_answer_key")
    elif item.item_type is DigiExamItemType.GAP_FILL:
        affordances.append("manual_gap_open_cloze_answer_key")
    return affordances


def _target_readiness(
    *,
    job_id: UUID,
    source_ir_sha256: str,
    effective_exam_sha256: str,
    blocked_item_ids: set[str],
    source_exam: DigiExamIntermediateExam,
) -> dict[str, JsonValue]:
    rows: list[JsonValue] = []
    blocked = bool(blocked_item_ids)
    for target, artifact_key in (("examnet_pdf", "examnet_pdf"), ("qti_package", "qti_package")):
        rows.append(_readiness_row(target, artifact_key, blocked, None))
        for item in source_exam.items:
            if item.item_id in blocked_item_ids:
                rows.append(_readiness_row(target, artifact_key, True, item))
    return {
        "schema_version": "target_readiness_report_v1",
        "job_id": str(job_id),
        "source_ir_sha256": source_ir_sha256,
        "effective_exam_sha256": effective_exam_sha256,
        "targets": rows,
    }


def _readiness_row(
    target: str,
    artifact_key: str,
    blocked: bool,
    item: DigiExamIrItem | None,
) -> dict[str, JsonValue]:
    return {
        "target": target,
        "readiness": "needs_teacher_answer_key" if blocked else "ready",
        "export_enabled": not blocked,
        "artifact_key": artifact_key,
        "reason_code": "manual_answer_key_required" if blocked else "ready",
        "teacher_action": "review_answer_key" if blocked else "none",
        "retryable": False,
        "message_key": (
            "exam_converter.target.needs_teacher_answer_key"
            if blocked
            else "exam_converter.target.ready"
        ),
        "item_id": item.item_id if item else None,
        "sequence": item.sequence if item else None,
        "source_item_fingerprint": source_item_fingerprint(item) if item else None,
    }


def _completion_report(
    *,
    source_exam: DigiExamIntermediateExam,
    proposal_overlay: DigiExamIngestionOverlay | None,
    provider_profile_id: str | None,
    model: str | None,
    failure_code: str | None,
    retry_identity: str | None,
) -> dict[str, JsonValue]:
    proposals = {
        item.item_id: item for item in (proposal_overlay.items if proposal_overlay else ())
    }
    items: list[JsonValue] = []
    for item in source_exam.items:
        proposal = proposals.get(item.item_id)
        payload = (
            proposal.manual_answer_key.model_dump(mode="json")
            if proposal and proposal.manual_answer_key
            else None
        )
        payload_bytes = _json_bytes(payload) if payload is not None else b""
        prompt_version = (
            GAP_FILL_PROMPT_TEMPLATE_VERSION
            if item.item_type is DigiExamItemType.GAP_FILL
            else CHOICE_PROMPT_TEMPLATE_VERSION
        )
        items.append(
            {
                "item_id": item.item_id,
                "sequence": item.sequence,
                "item_type": item.item_type.value,
                "decision_state": (
                    "suggested"
                    if payload is not None
                    else "manual_follow_up_required"
                    if failure_code is not None and item.item_type in _MACHINE_MARKED
                    else "skipped"
                ),
                "validation_state": "valid" if payload is not None else "skipped",
                "answer_payload": payload,
                "backend_status": (
                    "succeeded"
                    if payload is not None
                    else "failed"
                    if failure_code is not None and item.item_type in _MACHINE_MARKED
                    else "not_requested"
                ),
                "backend_failure_code": (
                    failure_code if item.item_type in _MACHINE_MARKED else None
                ),
                "retry_identity": (
                    retry_identity
                    if failure_code is not None and item.item_type in _MACHINE_MARKED
                    else None
                ),
                "candidate_id": f"candidate-{item.item_id}" if payload is not None else None,
                "candidate_payload_digest": _sha256(payload_bytes) if payload is not None else None,
                "provider_profile_id": provider_profile_id if payload is not None else None,
                "model_profile": model if payload is not None else None,
                "prompt_template_version": prompt_version if payload is not None else None,
                "schema_name": f"digiexam_{item.item_type.value}_answer_key_v1"
                if payload is not None
                else None,
                "schema_version": "1" if payload is not None else None,
            }
        )
    return {
        "schema_version": "answer_key_completion_report_v1",
        "completion_mode": "local_llm_suggest_missing_machine_marked",
        "items": items,
    }


def _artifact_entry(*, job_id: UUID, artifact: ExamConversionNamedArtifact) -> dict[str, JsonValue]:
    return {
        "artifact_key": artifact.artifact_key,
        "filename": artifact.filename,
        "content_type": artifact.content_type,
        "availability": "available",
        "size_bytes": len(artifact.content),
        "sha256": _sha256(artifact.content),
        "download_path": (
            f"/api/v1/apps/documents.conversion_hub/exam-converter/jobs/{job_id}/artifacts/"
            f"{artifact.artifact_key}"
        ),
        "unavailable_code": None,
    }


def _named(
    key: str, filename: str, content_type: str, content: bytes
) -> ExamConversionNamedArtifact:
    return ExamConversionNamedArtifact(
        artifact_key=key,
        filename=filename,
        content_type=content_type,
        content=content,
    )


def _sha256(content: bytes) -> str:
    return f"sha256:{hashlib.sha256(content).hexdigest()}"


def _json_bytes(
    value: JsonValue | DigiExamIntermediateExam | DigiExamEffectiveExam | DigiExamIrManifest,
) -> bytes:
    payload = (
        asdict(value)
        if not isinstance(value, str | int | float | bool | list | dict | type(None))
        else value
    )
    return (json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n").encode()
