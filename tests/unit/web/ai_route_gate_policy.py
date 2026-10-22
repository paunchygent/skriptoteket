"""Maintained policy for the paid-LLM sign-in route-coverage guard.

Purpose:
    Hold the one maintained input the guard derives everything else from: the
    paid LLM client protocols, the job enqueue/lane classification, the
    non-AI job-repository decisions, the expected paid-LLM route snapshot and
    the sign-in gate every AI route depends on, directly or through a role
    check. Editing policy here is a deliberate decision, never a way to make
    a failing guard assertion pass.

Relationships:
    - Consumed by `test_ai_route_gate_coverage.py` (assertions) and
      `ai_route_gate_discovery.py` (reachability and route classification).
    - The protocol and handler types are the production contracts under
      `src/skriptoteket/protocols/` and
      `src/skriptoteket/application/curated_apps/`.
"""

from __future__ import annotations

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import ExamAnswerKeySourceKind
from skriptoteket.application.curated_apps.handlers.exam_answer_key_enrichment_jobs import (
    ProcessExamAnswerKeyEnrichmentJobHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_content_tags import (
    ProcessExamContentSuggestionsHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_digiexam_jobs import (
    ProcessExamWorkspaceDigiExamJobHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_jobs import (
    ProcessExamWorkspaceDocxJobHandler,
)
from skriptoteket.protocols import llm as llm_protocols
from skriptoteket.protocols.exam_answer_key import AnswerKeyStructuredProviderProtocol
from skriptoteket.protocols.exam_workspace import (
    GetExamContentSuggestionsHandlerProtocol,
    GetExamWorkspaceAnswerKeySuggestionsStatusHandlerProtocol,
    GetExamWorkspaceConversionStatusHandlerProtocol,
    GetExamWorkspaceDocumentHandlerProtocol,
    ImportExamWorkspaceDigiExamDocumentHandlerProtocol,
    ImportExamWorkspaceDocumentHandlerProtocol,
    RequestExamContentSuggestionsHandlerProtocol,
    RequestExamWorkspaceAnswerKeySuggestionsHandlerProtocol,
    SaveExamWorkspaceDocumentHandlerProtocol,
)
from skriptoteket.protocols.exam_workspace_change_type import (
    ChangeExamWorkspaceItemTypeHandlerProtocol,
)
from skriptoteket.protocols.exam_workspace_guest_drafts import (
    ImportGuestExamDraftHandlerProtocol,
)
from skriptoteket.protocols.exam_workspace_history import (
    StoreExamWorkspaceUndoStepHandlerProtocol,
)
from skriptoteket.protocols.exam_workspace_parents import ExamWorkspaceParentsHandlerProtocol
from skriptoteket.protocols.item_type_labeler import (
    ExamContentTagClassifierProtocol,
    ItemTypeLabelerProtocol,
    MeteredItemTypeLabelerProtocol,
    SecondPassItemTypeLabelerProtocol,
)
from skriptoteket.web.auth.huleedu_app_projection import require_app_user_api

# The one maintained input: the paid LLM client protocols. Every class under
# `skriptoteket.infrastructure.llm` that implements one of these is a paid LLM
# client, and every DI type whose closure reaches one is an AI type.
PAID_LLM_PROTOCOLS: frozenset[type] = frozenset(
    {
        AnswerKeyStructuredProviderProtocol,
        # Content-classification port implemented by the paid
        # OpenAIDecisionsItemTypeLabeler (infrastructure/llm/openai/decisions_item_labeler.py),
        # which also serves the metered first pass.
        ExamContentTagClassifierProtocol,
        # Two-pass labeling port consumed by the DOCX pipeline's paid labelers.
        ItemTypeLabelerProtocol,
        MeteredItemTypeLabelerProtocol,
        SecondPassItemTypeLabelerProtocol,
        llm_protocols.InlineCompletionProviderProtocol,
        llm_protocols.ChatStreamProviderProtocol,
        llm_protocols.ChatOpsProviderProtocol,
    }
)

# Route-resolved handlers that enqueue a job the execution worker runs. Their
# own call path stops at enqueue, so the lane below decides whether the job
# spends money.
JOB_ENQUEUERS: dict[type, ExamAnswerKeySourceKind] = {
    RequestExamContentSuggestionsHandlerProtocol: ExamAnswerKeySourceKind.CONTENT_TAGS,
    ImportExamWorkspaceDocumentHandlerProtocol: ExamAnswerKeySourceKind.DOCX_IMPORT,
    RequestExamWorkspaceAnswerKeySuggestionsHandlerProtocol: ExamAnswerKeySourceKind.WORKSPACE,
}

# The worker handler each enqueued job kind runs.
JOB_LANES: dict[ExamAnswerKeySourceKind, type] = {
    ExamAnswerKeySourceKind.CONTENT_TAGS: ProcessExamContentSuggestionsHandler,
    ExamAnswerKeySourceKind.DOCX_IMPORT: ProcessExamWorkspaceDocxJobHandler,
    ExamAnswerKeySourceKind.WORKSPACE: ProcessExamAnswerKeyEnrichmentJobHandler,
    ExamAnswerKeySourceKind.DIGIEXAM_IMPORT: ProcessExamWorkspaceDigiExamJobHandler,
}

# Route-resolved Dishka types that use the exam answer-key job repository but
# make no LLM call. A new entry here is a decision: either it is a job enqueuer
# or the canonical gate test below also fails.
NON_AI_JOB_REPOSITORY_USERS: dict[type, str] = {
    ChangeExamWorkspaceItemTypeHandlerProtocol: "re-types one already-parsed item; no LLM call",
    ExamWorkspaceParentsHandlerProtocol: "reads the saved document and undo steps; no LLM call",
    GetExamContentSuggestionsHandlerProtocol: (
        "reads an enqueued content-tag job's status; no LLM call"
    ),
    GetExamWorkspaceAnswerKeySuggestionsStatusHandlerProtocol: (
        "reads an enqueued suggestion job's status; no LLM call"
    ),
    GetExamWorkspaceConversionStatusHandlerProtocol: "polls conversion progress; no LLM call",
    GetExamWorkspaceDocumentHandlerProtocol: "reopens the saved document; no LLM call",
    ImportExamWorkspaceDigiExamDocumentHandlerProtocol: (
        "enqueues DIGIEXAM_IMPORT, whose lane makes no LLM call"
    ),
    ImportGuestExamDraftHandlerProtocol: (
        "creates the exam from the posted guest draft; no LLM call"
    ),
    SaveExamWorkspaceDocumentHandlerProtocol: ("copies and reads document history; no LLM call"),
    StoreExamWorkspaceUndoStepHandlerProtocol: (
        "stores an autosave undo step and moves its position; no LLM call"
    ),
}

# The routes that can start a paid LLM call today, as (method, path) pairs.
EXPECTED_AI_ROUTES: frozenset[tuple[str, str]] = frozenset(
    {
        ("POST", "/api/v1/editor/completions"),
        ("POST", "/api/v1/editor/edit-ops"),
        ("POST", "/api/v1/editor/tools/{tool_id}/chat"),
        ("POST", "/api/v1/apps/documents.conversion_hub/exam-workspace/documents"),
        (
            "POST",
            "/api/v1/apps/documents.conversion_hub/exam-workspace"
            "/documents/{lineage_id}/items/retry",
        ),
        (
            "POST",
            "/api/v1/apps/documents.conversion_hub/exam-workspace"
            "/documents/{lineage_id}/content-suggestions",
        ),
        (
            "POST",
            "/api/v1/apps/documents.conversion_hub/exam-workspace"
            "/documents/{lineage_id}/answer-key-suggestions",
        ),
    }
)

# The sign-in gate every paid-LLM route depends on, directly or through a
# role check such as `require_app_contributor_api`. The guard walks the
# dependency chain, so a route carrying the contributor check counts as gated.
AI_ROLE_GATE = require_app_user_api
