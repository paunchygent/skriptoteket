from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from skriptoteket.protocols.llm import VirtualFileId


class UnifiedDiffHunk(BaseModel):
    model_config = ConfigDict(frozen=True)

    index: int
    header: str
    old_start: int
    old_count: int
    new_start: int
    new_count: int


class PreparedUnifiedDiff(BaseModel):
    model_config = ConfigDict(frozen=True)

    target_file: VirtualFileId
    normalized_diff: str
    patch_id: str
    normalizations_applied: list[str] = Field(default_factory=list)
    hunks: list[UnifiedDiffHunk] = Field(default_factory=list)


class PatchApplyMeta(BaseModel):
    model_config = ConfigDict(frozen=True)

    fuzz_level_used: int
    hunks_total: int
    offsets_per_hunk: list[int] = Field(default_factory=list)
    max_offset: int = 0
    whitespace_ignored: bool = False
    applied_cleanly: bool


class PatchApplyErrorDetails(BaseModel):
    model_config = ConfigDict(frozen=True)

    hunk_index: int | None = None
    hunk_header: str | None = None
    expected_snippet: str | None = None
    base_snippet: str | None = None


class PatchApplyResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    ok: bool
    next_text: str
    meta: PatchApplyMeta | None = None
    error: str | None = None
    error_details: PatchApplyErrorDetails | None = None


class UnifiedDiffApplierProtocol(Protocol):
    def prepare(self, *, target_file: VirtualFileId, unified_diff: str) -> PreparedUnifiedDiff: ...

    def apply(
        self,
        *,
        target_file: VirtualFileId,
        base_text: str,
        prepared: PreparedUnifiedDiff,
        max_fuzz: int,
        max_offset_lines: int,
        enable_whitespace_stage: bool,
    ) -> PatchApplyResult: ...
