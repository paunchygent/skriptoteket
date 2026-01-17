from __future__ import annotations

from skriptoteket.protocols.editor_patches import (
    PatchApplyResult,
    PreparedUnifiedDiff,
    UnifiedDiffApplierProtocol,
)
from skriptoteket.protocols.llm import VirtualFileId

from .unified_diff.apply_patch import apply_prepared_patch
from .unified_diff.normalize import prepare_unified_diff


class NativeUnifiedDiffApplier(UnifiedDiffApplierProtocol):
    def prepare(
        self,
        *,
        target_file: VirtualFileId,
        unified_diff: str,
        base_text: str | None = None,
    ) -> PreparedUnifiedDiff:
        return prepare_unified_diff(
            target_file=target_file,
            unified_diff=unified_diff,
            base_text=base_text,
        )

    def apply(
        self,
        *,
        target_file: VirtualFileId,
        base_text: str,
        prepared: PreparedUnifiedDiff,
        max_fuzz: int,
        max_offset_lines: int,
        enable_whitespace_stage: bool,
    ) -> PatchApplyResult:
        return apply_prepared_patch(
            target_file=target_file,
            base_text=base_text,
            prepared=prepared,
            max_fuzz=max_fuzz,
            max_offset_lines=max_offset_lines,
            enable_whitespace_stage=enable_whitespace_stage,
        )
