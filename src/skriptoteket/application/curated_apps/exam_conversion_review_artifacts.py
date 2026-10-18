"""Review, readiness, and artifact projections for public Exam Converter jobs.

Purpose:
    Project one parsed DigiExam source exam and its produced Exam.net bundle
    parts into the named artifacts and browser-facing manifest that the public
    guest Exam Converter stores, lists and serves for download.

Relationships:
    Called by ``application.curated_apps.exam_conversion_producers`` when the
    public converter produces a bundle; ``build_artifact_manifest`` is called by
    ``application.curated_apps.handlers.public_exam_converter_jobs`` over the
    stored named artifacts.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from uuid import UUID

from pydantic import JsonValue

from skriptoteket.application.curated_apps.exam_conversion import (
    ExamConversionNamedArtifact,
    build_examnet_pdf_filename,
    build_examnet_qti_filename,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_contracts import (
    DigiExamAnswerKeyProvenance,
    DigiExamItemType,
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
    qti_package_bytes: bytes,
    pdf_bytes: bytes,
    validation_report_bytes: bytes,
    enrichment_failure_code: str | None,
) -> tuple[ExamConversionNamedArtifact, ...]:
    """Build the complete local product projection from owned conversion state."""

    source_ir_bytes = _json_bytes(source_exam)
    source_ir_sha256 = _sha256(source_ir_bytes)
    review_state, blocked_item_ids = _review_state(source_exam=source_exam)
    readiness = _target_readiness(
        job_id=job_id,
        source_ir_sha256=source_ir_sha256,
        effective_exam_sha256=source_ir_sha256,
        blocked_item_ids=blocked_item_ids,
        source_exam=source_exam,
    )
    artifacts = [
        _named(
            "examnet_pdf",
            build_examnet_pdf_filename(input_filename=source_exam.source_filename),
            "application/pdf",
            pdf_bytes,
        ),
        _named(
            "qti_package",
            build_examnet_qti_filename(input_filename=source_exam.source_filename),
            "application/zip",
            qti_package_bytes,
        ),
        _named(
            "qti_validation_report",
            "qti-validation-report.json",
            "application/json",
            validation_report_bytes,
        ),
        _named("ir_json", "digiexam-ir.json", "application/json", source_ir_bytes),
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
    completion = _completion_report(source_exam=source_exam, failure_code=enrichment_failure_code)
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

    entries: list[JsonValue] = [_artifact_entry(artifact=artifact) for artifact in artifacts]
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
    source_ir_bytes = next(
        artifact.content for artifact in artifacts if artifact.artifact_key == "source_ir_json"
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
            "effective_exam_sha256": _sha256(source_ir_bytes),
        },
    }


def _review_state(
    *, source_exam: DigiExamIntermediateExam
) -> tuple[dict[str, JsonValue], set[str]]:
    rows: list[JsonValue] = []
    blocked_item_ids: set[str] = set()
    for item in source_exam.items:
        provenance = item.answer_key.provenance
        if provenance is not DigiExamAnswerKeyProvenance.ABSENT:
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
        if review_state == "validation_required":
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
                    f"choice-{value}" for value in item.answer_key.correct_alternative_ids
                ],
                "choice_interaction_ids": (
                    [f"choice-{item.item_id}"] if item.item_type in _MACHINE_MARKED else []
                ),
                "gap_ids": [answer.guid for answer in item.answer_key.correct_gap_answers],
                "gap_interaction_ids": (
                    [f"gap-{item.item_id}"] if item.item_type is DigiExamItemType.GAP_FILL else []
                ),
                "correction_affordances": _correction_affordances(item),
                "provenance_detail": None,
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
    failure_code: str | None,
) -> dict[str, JsonValue]:
    items: list[JsonValue] = []
    for item in source_exam.items:
        manual_follow_up = (
            failure_code is not None
            and item.answer_key.provenance is DigiExamAnswerKeyProvenance.ABSENT
            and item.item_type in _MACHINE_MARKED
        )
        items.append(
            {
                "item_id": item.item_id,
                "sequence": item.sequence,
                "item_type": item.item_type.value,
                "decision_state": "manual_follow_up_required" if manual_follow_up else "skipped",
                "validation_state": "manual_follow_up_required" if manual_follow_up else "skipped",
                "answer_payload": None,
                "backend_status": "failed" if manual_follow_up else "not_requested",
                "backend_failure_code": failure_code if manual_follow_up else None,
                "retry_identity": None,
                "candidate_id": None,
                "candidate_payload_digest": None,
                "provider_profile_id": None,
                "model_profile": None,
                "prompt_template_version": None,
                "schema_name": None,
                "schema_version": None,
            }
        )
    return {
        "schema_version": "answer_key_completion_report_v1",
        "completion_mode": "local_llm_suggest_missing_machine_marked",
        "items": items,
    }


def _artifact_entry(*, artifact: ExamConversionNamedArtifact) -> dict[str, JsonValue]:
    return {
        "artifact_key": artifact.artifact_key,
        "filename": artifact.filename,
        "content_type": artifact.content_type,
        "availability": "available",
        "size_bytes": len(artifact.content),
        "sha256": _sha256(artifact.content),
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


def _json_bytes(value: JsonValue | DigiExamIntermediateExam | DigiExamIrManifest) -> bytes:
    payload = (
        asdict(value)
        if not isinstance(value, str | int | float | bool | list | dict | type(None))
        else value
    )
    return (json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n").encode()
