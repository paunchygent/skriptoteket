"""Native document and immutable proposal records for save carry-forward proof."""

from datetime import datetime
from uuid import UUID, uuid4

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJob,
    ExamAnswerKeyEnrichmentJobStatus,
    ExamAnswerKeyProposedOverlay,
    ExamAnswerKeySourceKind,
)
from skriptoteket.domain.curated_apps.exam_workspace.answer_key_view import (
    AnswerKeyViewKind,
    WorkspaceAnswerKeyProposalRecord,
    WorkspaceAnswerKeyProposalsPayload,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)


def proposal_document() -> NativeExamDocument:
    review = {"state": "review_complete", "parse_origin": "teacher_created"}
    return NativeExamDocument.model_validate(
        {
            "document_id": str(uuid4()),
            "revision": 1,
            "title": "A small exam",
            "origin": {"kind": "created"},
            "items": [
                {
                    "item_id": "item_001",
                    "sequence": 1,
                    "kind": "single_choice",
                    "body": [{"segments": [{"kind": "text", "text": "Which word?"}]}],
                    "choices": [
                        {"choice_id": "choice_001", "text": "First"},
                        {"choice_id": "choice_002", "text": "Second"},
                    ],
                    "points": 1,
                    "answer_key": {"origin": "absent"},
                    "review": review,
                },
                {
                    "item_id": "item_002",
                    "sequence": 2,
                    "kind": "free_text",
                    "body": [{"segments": [{"kind": "text", "text": "Explain."}]}],
                    "points": 2,
                    "answer_key": {"origin": "not_applicable"},
                    "review": review,
                },
            ],
        }
    )


def proposal_ledger(
    *, owner_user_id: UUID, document: NativeExamDocument, now: datetime
) -> tuple[ExamAnswerKeyEnrichmentJob, ExamAnswerKeyProposedOverlay]:
    job = ExamAnswerKeyEnrichmentJob(
        id=uuid4(),
        owner_user_id=owner_user_id,
        source_kind=ExamAnswerKeySourceKind.WORKSPACE,
        status=ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED,
        input_filename="exam.provdokument.zip",
        workspace_lineage_id=document.document_id,
        workspace_document_revision=document.revision,
        attempts=1,
        available_at=now,
        created_at=now,
        updated_at=now,
        started_at=now,
        finished_at=now,
    )
    payload = WorkspaceAnswerKeyProposalsPayload(
        lineage_id=document.document_id,
        document_revision=document.revision,
        items=(
            WorkspaceAnswerKeyProposalRecord(
                item_id="item_001",
                kind=AnswerKeyViewKind.CHOICE,
                correct_choice_ids=("choice_002",),
                provider_profile_id="original-provider",
                model="original-model",
                prompt_template_version="original-prompt",
            ),
        ),
    )
    return job, ExamAnswerKeyProposedOverlay(
        id=uuid4(),
        enrichment_job_id=job.id,
        owner_user_id=owner_user_id,
        workspace_lineage_id=document.document_id,
        workspace_document_revision=document.revision,
        source_file_sha256="a" * 64,
        source_ir_sha256="b" * 64,
        provider_profile_id="original-provider",
        model="original-model",
        overlay_json=payload.model_dump(mode="json"),
        created_at=now,
    )


def saved_proposal_document(document: NativeExamDocument, scenario: str) -> NativeExamDocument:
    payload = document.model_dump(mode="json")
    payload["revision"] = document.revision + 1
    item = payload["items"][0]
    if scenario in {"teacher_authored", "reviewed_advisory"}:
        item["answer_key"] = {"origin": scenario, "correct_choice_ids": ["choice_002"]}
    elif scenario == "stale":
        item["body"][0]["segments"][0]["text"] = "A different question?"
    elif scenario == "deleted":
        payload["items"] = [payload["items"][1]]
        payload["items"][0]["sequence"] = 1
    else:
        payload["items"][1]["points"] = 3
    return NativeExamDocument.model_validate(payload)
