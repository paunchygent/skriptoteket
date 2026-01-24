from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from skriptoteket.domain.scripting.tool_inputs import ToolInputField
from skriptoteket.domain.scripting.ui.contract_v2 import UiActionField
from skriptoteket.protocols.llm import VirtualFileId
from skriptoteket.web.editor_support import DEFAULT_ENTRYPOINT

from .common import (
    EditorEditOpsCursor,
    EditorEditOpsOp,
    EditorEditOpsSelection,
    EditorVirtualFiles,
)


class EditorEditOpsRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    message: str = Field(min_length=1)
    active_file: VirtualFileId
    selection: EditorEditOpsSelection | None = None
    cursor: EditorEditOpsCursor | None = None
    virtual_files: EditorVirtualFiles

    @model_validator(mode="after")
    def validate_active_file(self) -> "EditorEditOpsRequest":
        if self.active_file not in self.virtual_files.as_map():
            raise ValueError("Active file is missing from virtual_files")
        return self


class EditorEditOpsPreviewRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    active_file: VirtualFileId
    selection: EditorEditOpsSelection | None = None
    cursor: EditorEditOpsCursor | None = None
    virtual_files: EditorVirtualFiles
    ops: list[EditorEditOpsOp]


class EditorEditOpsApplyRequest(EditorEditOpsPreviewRequest):
    model_config = ConfigDict(frozen=True)

    base_hash: str
    patch_id: str


class EditorChatRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    message: str = Field(min_length=1)
    base_version_id: UUID | None = None
    active_file: VirtualFileId | None = None
    virtual_files: EditorVirtualFiles | None = None

    @model_validator(mode="after")
    def validate_virtual_file_context(self) -> "EditorChatRequest":
        if self.active_file is not None and self.virtual_files is None:
            raise ValueError("virtual_files is required when active_file is provided")
        if self.virtual_files is not None and self.active_file is not None:
            if self.active_file not in self.virtual_files.as_map():
                raise ValueError("Active file is missing from virtual_files")
        return self


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


class SubmitReviewRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    review_note: str | None = None


class PublishVersionRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    change_summary: str | None = None


class RequestChangesRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    message: str | None = None


class SandboxSettingsResolveRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    settings_schema: list[UiActionField] | None = None


class SandboxSettingsSaveRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    settings_schema: list[UiActionField] | None = None
    expected_state_rev: int
    values: dict[str, JsonValue] = Field(default_factory=dict)


class ToolTaxonomyRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    profession_ids: list[UUID]
    category_ids: list[UUID]


class EditorToolMetadataRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    title: str
    summary: str | None = None


class EditorToolSlugRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    slug: str


class AssignMaintainerRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    email: str


class StartSandboxActionRequest(BaseModel):
    """Request for POST /api/v1/editor/tool-versions/{version_id}/start-action."""

    model_config = ConfigDict(frozen=True)

    snapshot_id: UUID
    action_id: str
    input: dict[str, JsonValue] = Field(default_factory=dict)
    file_refs: list[str] = Field(default_factory=list)
    expected_state_rev: int


class EditorInlineCompletionRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    prefix: str
    suffix: str
    active_file: VirtualFileId = "tool.py"


class ValidateToolSchemasRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    settings_schema: JsonValue | None = None
    input_schema: JsonValue | None = None
