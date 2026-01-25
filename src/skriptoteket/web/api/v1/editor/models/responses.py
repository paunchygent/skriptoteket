from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from skriptoteket.application.scripting.commands import SchemaValidationIssue
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.scripting.models import RunStatus, VersionState
from skriptoteket.domain.scripting.tool_inputs import ToolInputField
from skriptoteket.domain.scripting.ui.contract_v2 import UiActionField, UiPayloadV2
from skriptoteket.protocols.llm import VirtualFileId

from .common import EditorEditOpsOp, EditorVirtualFiles

EditorSaveMode = Literal["snapshot", "create_draft"]


class EditorToolSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    slug: str
    title: str
    summary: str | None
    is_published: bool
    active_version_id: UUID | None


class EditorVersionSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    version_number: int
    state: VersionState
    created_at: datetime
    reviewed_at: datetime | None
    published_at: datetime | None


class DraftLockResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    draft_head_id: UUID
    locked_by_user_id: UUID
    expires_at: datetime
    is_owner: bool


class EditorBootResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool: EditorToolSummary
    versions: list[EditorVersionSummary]
    selected_version: EditorVersionSummary | None
    draft_head_id: UUID | None
    draft_lock: DraftLockResponse | None
    save_mode: EditorSaveMode
    parent_version_id: UUID | None
    create_draft_from_version_id: UUID | None
    entrypoint: str
    source_code: str
    settings_schema: list[UiActionField] | None = None
    input_schema: list[ToolInputField] = Field(default_factory=list)
    usage_instructions: str | None = None


class EditorEditOpsResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    enabled: bool
    assistant_message: str
    ops: list[EditorEditOpsOp]
    base_fingerprints: dict[VirtualFileId, str]


class EditorEditOpsPreviewMeta(BaseModel):
    model_config = ConfigDict(frozen=True)

    base_hash: str
    patch_id: str
    requires_confirmation: bool
    fuzz_level_used: int = 0
    max_offset: int = 0
    normalizations_applied: list[str] = Field(default_factory=list)
    applied_cleanly: bool = True


class EditorEditOpsPreviewErrorDetails(BaseModel):
    model_config = ConfigDict(frozen=True)

    op_index: int | None = None
    target_file: VirtualFileId | None = None
    hunk_index: int | None = None
    hunk_header: str | None = None
    expected_snippet: str | None = None
    base_snippet: str | None = None


class EditorEditOpsPreviewResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    ok: bool
    after_virtual_files: EditorVirtualFiles
    errors: list[str] = Field(default_factory=list)
    error_details: list[EditorEditOpsPreviewErrorDetails] = Field(default_factory=list)
    meta: EditorEditOpsPreviewMeta


class EditorChatHistoryMessage(BaseModel):
    model_config = ConfigDict(frozen=True)

    message_id: UUID
    turn_id: UUID
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime
    status: Literal["pending", "complete", "failed", "cancelled"]
    correlation_id: UUID | None = None
    failure_outcome: str | None = None


class EditorChatHistoryResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    messages: list[EditorChatHistoryMessage] = Field(default_factory=list)
    base_version_id: UUID | None = None


class DraftLockReleaseResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID


class SaveResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    version_id: UUID
    redirect_url: str


class WorkflowActionResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    version_id: UUID
    redirect_url: str


class SandboxRunResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: UUID
    status: RunStatus
    started_at: datetime
    state_rev: int | None = None  # Populated when run has next_actions (ADR-0038)
    snapshot_id: UUID


class SandboxSettingsResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    schema_version: str | None
    settings_schema: list[UiActionField] | None
    values: dict[str, JsonValue]
    state_rev: int


class ArtifactEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    artifact_id: str
    path: str
    bytes: int
    download_url: str


class EditorRunDetails(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: UUID
    version_id: UUID | None
    snapshot_id: UUID | None
    status: RunStatus
    started_at: datetime
    finished_at: datetime | None
    error_summary: str | None
    stdout: str | None = None
    stderr: str | None = None
    stdout_bytes: int | None = None
    stderr_bytes: int | None = None
    stdout_max_bytes: int | None = None
    stderr_max_bytes: int | None = None
    stdout_truncated: bool | None = None
    stderr_truncated: bool | None = None
    ui_payload: UiPayloadV2 | None
    artifacts: list[ArtifactEntry]


class ToolTaxonomyResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    profession_ids: list[UUID]
    category_ids: list[UUID]


class EditorToolMetadataResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    slug: str
    title: str
    summary: str | None


class MaintainerSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    email: str
    role: Role


class MaintainerListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    owner_user_id: UUID
    maintainers: list[MaintainerSummary]


class SandboxSessionResponse(BaseModel):
    """Response for GET /api/v1/editor/tool-versions/{version_id}/session."""

    model_config = ConfigDict(frozen=True)

    state_rev: int
    state: dict[str, JsonValue] | None = None


class EditorInlineCompletionResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    completion: str
    enabled: bool
    replace_suffix_chars: int | None = Field(default=None, ge=0)
    notice_message: str | None = None
    notice_variant: Literal["info", "warning"] | None = None
    notice_code: str | None = None


class StartSandboxActionResponse(BaseModel):
    """Response for POST /api/v1/editor/tool-versions/{version_id}/start-action."""

    model_config = ConfigDict(frozen=True)

    run_id: UUID
    state_rev: int


class ValidateToolSchemasResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    valid: bool
    issues: list[SchemaValidationIssue] = Field(default_factory=list)
