from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from skriptoteket.application.scripting.commands import SchemaValidationIssue
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.scripting.models import RunStatus, VersionState
from skriptoteket.domain.scripting.tool_inputs import ToolInputField
from skriptoteket.domain.scripting.ui.contract_v2 import UiActionField
from skriptoteket.web.editor_support import DEFAULT_ENTRYPOINT

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


class EditorEditSuggestionRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    prefix: str
    selection: str
    suffix: str
    instruction: str | None = None


class EditorEditSuggestionResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    suggestion: str
    enabled: bool


class EditorChatRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    message: str = Field(min_length=1)


class CreateDraftVersionRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    entrypoint: str = DEFAULT_ENTRYPOINT
    source_code: str
    settings_schema: list[UiActionField] | None = None
    input_schema: list[ToolInputField] = Field(default_factory=list)
    usage_instructions: str | None = None
    change_summary: str | None = None
    derived_from_version_id: UUID | None = None


class SaveDraftVersionRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    entrypoint: str = DEFAULT_ENTRYPOINT
    source_code: str
    settings_schema: list[UiActionField] | None = None
    input_schema: list[ToolInputField] = Field(default_factory=list)
    usage_instructions: str | None = None
    change_summary: str | None = None
    expected_parent_version_id: UUID


class DraftLockRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    draft_head_id: UUID
    force: bool = False


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


class SubmitReviewRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    review_note: str | None = None


class PublishVersionRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    change_summary: str | None = None


class RequestChangesRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    message: str | None = None


class SandboxRunResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: UUID
    status: RunStatus
    started_at: datetime
    state_rev: int | None = None  # Populated when run has next_actions (ADR-0038)
    snapshot_id: UUID


class SandboxSettingsResolveRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    settings_schema: list[UiActionField] | None = None


class SandboxSettingsSaveRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    settings_schema: list[UiActionField] | None = None
    expected_state_rev: int
    values: dict[str, JsonValue] = Field(default_factory=dict)


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
    ui_payload: dict | None
    artifacts: list[ArtifactEntry]


class ToolTaxonomyResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    profession_ids: list[UUID]
    category_ids: list[UUID]


class ToolTaxonomyRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    profession_ids: list[UUID]
    category_ids: list[UUID]


class EditorToolMetadataResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    slug: str
    title: str
    summary: str | None


class EditorToolMetadataRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    title: str
    summary: str | None = None


class EditorToolSlugRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    slug: str


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


class AssignMaintainerRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    email: str


class SandboxSessionResponse(BaseModel):
    """Response for GET /api/v1/editor/tool-versions/{version_id}/session."""

    model_config = ConfigDict(frozen=True)

    state_rev: int
    state: dict[str, JsonValue] | None = None


class StartSandboxActionRequest(BaseModel):
    """Request for POST /api/v1/editor/tool-versions/{version_id}/start-action."""

    model_config = ConfigDict(frozen=True)

    snapshot_id: UUID
    action_id: str
    input: dict[str, JsonValue] = Field(default_factory=dict)
    expected_state_rev: int


class EditorInlineCompletionRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    prefix: str
    suffix: str


class EditorInlineCompletionResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    completion: str
    enabled: bool


class StartSandboxActionResponse(BaseModel):
    """Response for POST /api/v1/editor/tool-versions/{version_id}/start-action."""

    model_config = ConfigDict(frozen=True)

    run_id: UUID
    state_rev: int


class ValidateToolSchemasRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    settings_schema: JsonValue | None = None
    input_schema: JsonValue | None = None


class ValidateToolSchemasResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    valid: bool
    issues: list[SchemaValidationIssue] = Field(default_factory=list)
