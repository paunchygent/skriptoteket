from fastapi import APIRouter

from . import (
    boot,
    chat,
    completions,
    drafts,
    edits,
    locks,
    maintainers,
    metadata,
    runs,
    sandbox,
    sandbox_settings,
    schema_validation,
    taxonomy,
    workflow,
)
from .boot import get_editor_for_tool, get_editor_for_version
from .chat import clear_editor_chat, stream_editor_chat
from .completions import create_inline_completion
from .drafts import create_draft_version, save_draft_version
from .edits import create_edit_suggestion
from .locks import acquire_draft_lock, release_draft_lock
from .maintainers import (
    assign_tool_maintainer,
    list_tool_maintainers,
    remove_tool_maintainer,
)
from .metadata import update_tool_metadata, update_tool_slug
from .models import (
    AssignMaintainerRequest,
    CreateDraftVersionRequest,
    DraftLockReleaseResponse,
    DraftLockRequest,
    DraftLockResponse,
    EditorBootResponse,
    EditorChatRequest,
    EditorEditSuggestionRequest,
    EditorEditSuggestionResponse,
    EditorInlineCompletionRequest,
    EditorInlineCompletionResponse,
    EditorRunDetails,
    EditorSaveMode,
    EditorToolMetadataRequest,
    EditorToolMetadataResponse,
    EditorToolSlugRequest,
    EditorToolSummary,
    EditorVersionSummary,
    MaintainerListResponse,
    MaintainerSummary,
    PublishVersionRequest,
    RequestChangesRequest,
    SandboxRunResponse,
    SandboxSessionResponse,
    SandboxSettingsResolveRequest,
    SandboxSettingsResponse,
    SandboxSettingsSaveRequest,
    SaveDraftVersionRequest,
    SaveResult,
    StartSandboxActionRequest,
    StartSandboxActionResponse,
    SubmitReviewRequest,
    ToolTaxonomyRequest,
    ToolTaxonomyResponse,
    ValidateToolSchemasRequest,
    ValidateToolSchemasResponse,
    WorkflowActionResponse,
)
from .runs import download_artifact, get_run
from .sandbox import get_sandbox_session, run_sandbox, start_sandbox_action
from .sandbox_settings import resolve_sandbox_settings, save_sandbox_settings
from .schema_validation import validate_schemas
from .taxonomy import get_tool_taxonomy, update_tool_taxonomy
from .workflow import publish_version, request_changes, rollback_version, submit_review

router = APIRouter(prefix="/api/v1/editor", tags=["editor"])
router.include_router(boot.router)
router.include_router(locks.router)
router.include_router(taxonomy.router)
router.include_router(metadata.router)
router.include_router(maintainers.router)
router.include_router(drafts.router)
router.include_router(workflow.router)
router.include_router(sandbox.router)
router.include_router(sandbox_settings.router)
router.include_router(schema_validation.router)
router.include_router(runs.router)
router.include_router(completions.router)
router.include_router(edits.router)
router.include_router(chat.router)

__all__ = [
    "AssignMaintainerRequest",
    "CreateDraftVersionRequest",
    "DraftLockReleaseResponse",
    "DraftLockRequest",
    "DraftLockResponse",
    "EditorBootResponse",
    "EditorChatRequest",
    "EditorEditSuggestionRequest",
    "EditorEditSuggestionResponse",
    "EditorInlineCompletionRequest",
    "EditorInlineCompletionResponse",
    "EditorRunDetails",
    "EditorSaveMode",
    "EditorToolMetadataRequest",
    "EditorToolMetadataResponse",
    "EditorToolSlugRequest",
    "EditorToolSummary",
    "EditorVersionSummary",
    "MaintainerListResponse",
    "MaintainerSummary",
    "PublishVersionRequest",
    "RequestChangesRequest",
    "SandboxRunResponse",
    "SandboxSettingsResolveRequest",
    "SandboxSettingsResponse",
    "SandboxSettingsSaveRequest",
    "SandboxSessionResponse",
    "SaveDraftVersionRequest",
    "SaveResult",
    "StartSandboxActionRequest",
    "StartSandboxActionResponse",
    "SubmitReviewRequest",
    "ToolTaxonomyRequest",
    "ToolTaxonomyResponse",
    "ValidateToolSchemasRequest",
    "ValidateToolSchemasResponse",
    "WorkflowActionResponse",
    "acquire_draft_lock",
    "assign_tool_maintainer",
    "create_draft_version",
    "create_edit_suggestion",
    "create_inline_completion",
    "clear_editor_chat",
    "download_artifact",
    "get_editor_for_tool",
    "get_editor_for_version",
    "get_run",
    "get_sandbox_session",
    "get_tool_taxonomy",
    "list_tool_maintainers",
    "publish_version",
    "release_draft_lock",
    "remove_tool_maintainer",
    "request_changes",
    "rollback_version",
    "run_sandbox",
    "resolve_sandbox_settings",
    "save_draft_version",
    "save_sandbox_settings",
    "start_sandbox_action",
    "stream_editor_chat",
    "submit_review",
    "validate_schemas",
    "update_tool_metadata",
    "update_tool_slug",
    "update_tool_taxonomy",
]
