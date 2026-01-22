"""Edit-ops protocol types."""

from __future__ import annotations

from typing import Literal, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from skriptoteket.domain.identity.models import User

from .common import VirtualFileId
from .eval import PromptEvalMeta


class EditOpsSelection(BaseModel):
    model_config = ConfigDict(frozen=True)

    start: int
    end: int

    @model_validator(mode="after")
    def validate_range(self) -> "EditOpsSelection":
        if self.end < self.start:
            raise ValueError("Selection end must be >= start")
        return self


class EditOpsCursor(BaseModel):
    model_config = ConfigDict(frozen=True)

    pos: int


class EditOpsPatchOp(BaseModel):
    model_config = ConfigDict(frozen=True)

    op: Literal["patch"]
    target_file: VirtualFileId
    patch_lines: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_patch_shape(self) -> "EditOpsPatchOp":
        """Light validation; backend is responsible for robust sanitization + apply.

        We accept slightly malformed headers to reduce regeneration loops, but still reject
        obvious multi-file diffs and wrong-file targets when headers are present.
        """

        for line in self.patch_lines:
            if "\n" in line or "\r" in line:
                raise ValueError("Patch lines must not contain newline characters")

        def basename(path: str) -> str:
            cleaned = path
            if cleaned.startswith(("a/", "b/")):
                cleaned = cleaned[2:]
            if cleaned.startswith("./"):
                cleaned = cleaned[2:]
            return cleaned

        old_path: str | None = None
        new_path: str | None = None
        diff_git_paths: tuple[str | None, str | None] = (None, None)

        diff_git_count = 0
        header_old_count = 0
        header_new_count = 0

        for line in self.patch_lines:
            if line.startswith("diff --git "):
                diff_git_count += 1
                parts = line.split()
                if len(parts) >= 4 and diff_git_paths == (None, None):
                    diff_git_paths = (parts[2], parts[3])
                continue

            if line.startswith("--- "):
                header_old_count += 1
                if old_path is None:
                    parts = line.split()
                    if len(parts) >= 2:
                        old_path = parts[1]
                continue

            if line.startswith("+++ "):
                header_new_count += 1
                if new_path is None:
                    parts = line.split()
                    if len(parts) >= 2:
                        new_path = parts[1]
                continue

        if diff_git_count > 1 or header_old_count > 1 or header_new_count > 1:
            raise ValueError("Patch must only touch one file")

        git_old, git_new = diff_git_paths
        if git_old and git_new:
            if git_old == "/dev/null" or git_new == "/dev/null":
                raise ValueError("Patch must not create or delete files")
            if basename(git_old) != self.target_file or basename(git_new) != self.target_file:
                raise ValueError("Patch targets a different file than target_file")

        if old_path and new_path:
            if old_path == "/dev/null" or new_path == "/dev/null":
                raise ValueError("Patch must not create or delete files")
            if basename(old_path) != self.target_file or basename(new_path) != self.target_file:
                raise ValueError("Patch targets a different file than target_file")

        return self


EditOpsOp = EditOpsPatchOp


class EditOpsCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    message: str
    active_file: VirtualFileId
    selection: EditOpsSelection | None = None
    cursor: EditOpsCursor | None = None
    virtual_files: dict[VirtualFileId, str]
    allow_remote_fallback: bool | None = None


class EditOpsResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    enabled: bool
    assistant_message: str
    ops: list[EditOpsOp]
    base_fingerprints: dict[VirtualFileId, str]
    eval_meta: PromptEvalMeta | None = None


class EditOpsPreviewCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    active_file: VirtualFileId
    selection: EditOpsSelection | None = None
    cursor: EditOpsCursor | None = None
    virtual_files: dict[VirtualFileId, str]
    ops: list[EditOpsOp]


class EditOpsPreviewMeta(BaseModel):
    model_config = ConfigDict(frozen=True)

    base_hash: str
    patch_id: str
    requires_confirmation: bool
    fuzz_level_used: int = 0
    max_offset: int = 0
    normalizations_applied: list[str] = Field(default_factory=list)
    applied_cleanly: bool = True


class EditOpsPreviewErrorDetails(BaseModel):
    model_config = ConfigDict(frozen=True)

    op_index: int | None = None
    target_file: VirtualFileId | None = None
    hunk_index: int | None = None
    hunk_header: str | None = None
    expected_snippet: str | None = None
    base_snippet: str | None = None


class EditOpsPreviewResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    ok: bool
    after_virtual_files: dict[VirtualFileId, str]
    errors: list[str]
    error_details: list[EditOpsPreviewErrorDetails] = Field(default_factory=list)
    meta: EditOpsPreviewMeta


class EditOpsApplyCommand(EditOpsPreviewCommand):
    model_config = ConfigDict(frozen=True)

    base_hash: str
    patch_id: str


class EditOpsHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        command: EditOpsCommand,
    ) -> EditOpsResult: ...


class EditOpsPreviewHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        command: EditOpsPreviewCommand,
    ) -> EditOpsPreviewResult: ...


class EditOpsApplyHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        command: EditOpsApplyCommand,
    ) -> EditOpsPreviewResult: ...
