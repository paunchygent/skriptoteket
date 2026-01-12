from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from skriptoteket.application.scripting.commands import SchemaValidationIssue
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.scripting.models import RunStatus, VersionState
from skriptoteket.domain.scripting.tool_inputs import ToolInputField
from skriptoteket.domain.scripting.ui.contract_v2 import UiActionField
from skriptoteket.protocols.llm import VirtualFileId
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


class EditorEditOpsSelection(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    start: int = Field(alias="from", ge=0)
    end: int = Field(alias="to", ge=0)

    @model_validator(mode="after")
    def validate_range(self) -> "EditorEditOpsSelection":
        if self.end < self.start:
            raise ValueError("Selection end must be >= start")
        return self


class EditorEditOpsCursor(BaseModel):
    model_config = ConfigDict(frozen=True)

    pos: int = Field(ge=0)


class EditorVirtualFiles(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    tool_py: str = Field(alias="tool.py")
    entrypoint_txt: str = Field(alias="entrypoint.txt")
    settings_schema_json: str = Field(alias="settings_schema.json")
    input_schema_json: str = Field(alias="input_schema.json")
    usage_instructions_md: str = Field(alias="usage_instructions.md")

    def as_map(self) -> dict[VirtualFileId, str]:
        return {
            "tool.py": self.tool_py,
            "entrypoint.txt": self.entrypoint_txt,
            "settings_schema.json": self.settings_schema_json,
            "input_schema.json": self.input_schema_json,
            "usage_instructions.md": self.usage_instructions_md,
        }


class EditorEditOpsRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    message: str = Field(min_length=1)
    allow_remote_fallback: bool = False
    active_file: VirtualFileId
    selection: EditorEditOpsSelection | None = None
    cursor: EditorEditOpsCursor | None = None
    virtual_files: EditorVirtualFiles

    @model_validator(mode="after")
    def validate_active_file(self) -> "EditorEditOpsRequest":
        if self.active_file not in self.virtual_files.as_map():
            raise ValueError("Active file is missing from virtual_files")
        return self


class EditorEditOpsAnchor(BaseModel):
    model_config = ConfigDict(frozen=True)

    match: str = Field(min_length=1)
    placement: Literal["before", "after"] | None = None


class EditorEditOpsCursorTarget(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal["cursor"]


class EditorEditOpsSelectionTarget(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal["selection"]


class EditorEditOpsDocumentTarget(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal["document"]


class EditorEditOpsAnchorTarget(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal["anchor"]
    anchor: EditorEditOpsAnchor


EditorEditOpsTarget = Annotated[
    EditorEditOpsCursorTarget
    | EditorEditOpsSelectionTarget
    | EditorEditOpsDocumentTarget
    | EditorEditOpsAnchorTarget,
    Field(discriminator="kind"),
]


class EditorEditOpsInsertOp(BaseModel):
    model_config = ConfigDict(frozen=True)

    op: Literal["insert"]
    target_file: VirtualFileId
    target: EditorEditOpsTarget
    content: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_insert(self) -> "EditorEditOpsInsertOp":
        if self.target.kind not in {"cursor", "anchor"}:
            raise ValueError("Insert ops must target cursor or anchor")
        if self.target.kind == "anchor" and self.target.anchor.placement is None:
            raise ValueError("Anchor placement is required for insert ops")
        return self


class EditorEditOpsReplaceOp(BaseModel):
    model_config = ConfigDict(frozen=True)

    op: Literal["replace"]
    target_file: VirtualFileId
    target: EditorEditOpsTarget
    content: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_replace(self) -> "EditorEditOpsReplaceOp":
        if self.target.kind == "cursor":
            raise ValueError("Replace ops must target selection, document, or anchor")
        return self


class EditorEditOpsDeleteOp(BaseModel):
    model_config = ConfigDict(frozen=True)

    op: Literal["delete"]
    target_file: VirtualFileId
    target: EditorEditOpsTarget
    content: None = None

    @model_validator(mode="after")
    def validate_delete(self) -> "EditorEditOpsDeleteOp":
        if self.target.kind == "cursor":
            raise ValueError("Delete ops must target selection, document, or anchor")
        return self


class EditorEditOpsPatchOp(BaseModel):
    model_config = ConfigDict(frozen=True)

    op: Literal["patch"]
    target_file: VirtualFileId
    patch: str = Field(min_length=1)


EditorEditOpsOp = Annotated[
    EditorEditOpsInsertOp | EditorEditOpsReplaceOp | EditorEditOpsDeleteOp | EditorEditOpsPatchOp,
    Field(discriminator="op"),
]


class EditorEditOpsResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    enabled: bool
    assistant_message: str
    ops: list[EditorEditOpsOp]
    base_fingerprints: dict[VirtualFileId, str]


class EditorEditOpsPreviewRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    active_file: VirtualFileId
    selection: EditorEditOpsSelection | None = None
    cursor: EditorEditOpsCursor | None = None
    virtual_files: EditorVirtualFiles
    ops: list[EditorEditOpsOp]


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


class EditorEditOpsApplyRequest(EditorEditOpsPreviewRequest):
    model_config = ConfigDict(frozen=True)

    base_hash: str
    patch_id: str


class EditorChatRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    message: str = Field(min_length=1)
    base_version_id: UUID | None = None
    allow_remote_fallback: bool = False


class EditorChatHistoryMessage(BaseModel):
    model_config = ConfigDict(frozen=True)

    message_id: UUID
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime


class EditorChatHistoryResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    messages: list[EditorChatHistoryMessage] = Field(default_factory=list)
    base_version_id: UUID | None = None


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
