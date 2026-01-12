from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from skriptoteket.application.editor.edit_ops_preview_handler import (
    EditOpsApplyHandler,
    EditOpsPreviewHandler,
)
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role
from skriptoteket.protocols.editor_patches import (
    PatchApplyMeta,
    PatchApplyResult,
    PreparedUnifiedDiff,
    UnifiedDiffHunk,
)
from skriptoteket.protocols.llm import (
    EditOpsApplyCommand,
    EditOpsDocumentTarget,
    EditOpsPatchOp,
    EditOpsPreviewCommand,
    EditOpsReplaceOp,
)
from tests.fixtures.identity_fixtures import make_user


class StubCaptureStore:
    async def write_capture(self, *, kind: str, capture_id, payload) -> None:  # type: ignore[no-untyped-def]
        return


class StubPatchApplier:
    def prepare(self, *, target_file: str, unified_diff: str) -> PreparedUnifiedDiff:
        return PreparedUnifiedDiff(
            target_file=target_file,
            normalized_diff=unified_diff,
            patch_id="sha256:stub-patch",
            normalizations_applied=["stripped_code_fences"],
            hunks=[
                UnifiedDiffHunk(
                    index=1,
                    header="@@ -1 +1 @@",
                    old_start=1,
                    old_count=1,
                    new_start=1,
                    new_count=1,
                )
            ],
        )

    def apply(
        self,
        *,
        target_file: str,
        base_text: str,
        prepared: PreparedUnifiedDiff,
        max_fuzz: int,
        max_offset_lines: int,
        enable_whitespace_stage: bool,
    ) -> PatchApplyResult:
        return PatchApplyResult(
            ok=True,
            next_text=base_text + "# patched\n",
            meta=PatchApplyMeta(
                fuzz_level_used=0,
                hunks_total=len(prepared.hunks),
                offsets_per_hunk=[11],
                max_offset=11,
                whitespace_ignored=False,
                applied_cleanly=False,
            ),
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_preview_requires_confirmation_when_patch_offset_high() -> None:
    actor = make_user(role=Role.CONTRIBUTOR)
    handler = EditOpsPreviewHandler(
        settings=Settings(),
        capture_store=StubCaptureStore(),
        patch_applier=StubPatchApplier(),
    )

    result = await handler.handle(
        actor=actor,
        command=EditOpsPreviewCommand(
            tool_id=uuid4(),
            active_file="tool.py",
            selection=None,
            cursor=None,
            virtual_files={"tool.py": "print('hi')\n"},
            ops=[
                EditOpsPatchOp(
                    op="patch",
                    target_file="tool.py",
                    patch="@@ -1 +1 @@\n-print('hi')\n+print('hello')\n",
                )
            ],
        ),
    )

    assert result.ok is True
    assert result.meta.requires_confirmation is True
    assert result.meta.max_offset == 11
    assert result.after_virtual_files["tool.py"].endswith("# patched\n")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_rejects_when_base_hash_mismatch() -> None:
    actor = make_user(role=Role.CONTRIBUTOR)
    preview_handler = EditOpsPreviewHandler(
        settings=Settings(),
        capture_store=StubCaptureStore(),
        patch_applier=MagicMock(),
    )
    apply_handler = EditOpsApplyHandler(preview=preview_handler)

    with pytest.raises(DomainError) as exc_info:
        await apply_handler.handle(
            actor=actor,
            command=EditOpsApplyCommand(
                tool_id=uuid4(),
                active_file="tool.py",
                selection=None,
                cursor=None,
                virtual_files={"tool.py": "print('hi')\n"},
                ops=[
                    EditOpsReplaceOp(
                        op="replace",
                        target_file="tool.py",
                        target=EditOpsDocumentTarget(kind="document"),
                        content="print('bye')\n",
                    )
                ],
                base_hash="sha256:bad",
                patch_id="sha256:bad",
            ),
        )

    assert exc_info.value.code is ErrorCode.CONFLICT


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_rejects_when_patch_id_mismatch() -> None:
    actor = make_user(role=Role.CONTRIBUTOR)
    preview_handler = EditOpsPreviewHandler(
        settings=Settings(),
        capture_store=StubCaptureStore(),
        patch_applier=MagicMock(),
    )
    apply_handler = EditOpsApplyHandler(preview=preview_handler)

    tool_id = uuid4()
    virtual_files = {"tool.py": "print('hi')\n"}
    ops = [
        EditOpsReplaceOp(
            op="replace",
            target_file="tool.py",
            target=EditOpsDocumentTarget(kind="document"),
            content="print('bye')\n",
        )
    ]

    preview = await preview_handler.handle(
        actor=actor,
        command=EditOpsPreviewCommand(
            tool_id=tool_id,
            active_file="tool.py",
            selection=None,
            cursor=None,
            virtual_files=virtual_files,
            ops=ops,
        ),
    )

    with pytest.raises(DomainError) as exc_info:
        await apply_handler.handle(
            actor=actor,
            command=EditOpsApplyCommand(
                tool_id=tool_id,
                active_file="tool.py",
                selection=None,
                cursor=None,
                virtual_files=virtual_files,
                ops=ops,
                base_hash=preview.meta.base_hash,
                patch_id="sha256:bad",
            ),
        )

    assert exc_info.value.code is ErrorCode.CONFLICT


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_returns_preview_result_when_tokens_match() -> None:
    actor = make_user(role=Role.CONTRIBUTOR)
    preview_handler = EditOpsPreviewHandler(
        settings=Settings(),
        capture_store=StubCaptureStore(),
        patch_applier=MagicMock(),
    )
    apply_handler = EditOpsApplyHandler(preview=preview_handler)

    tool_id = uuid4()
    virtual_files = {"tool.py": "print('hi')\n"}
    ops = [
        EditOpsReplaceOp(
            op="replace",
            target_file="tool.py",
            target=EditOpsDocumentTarget(kind="document"),
            content="print('bye')\n",
        )
    ]

    preview = await preview_handler.handle(
        actor=actor,
        command=EditOpsPreviewCommand(
            tool_id=tool_id,
            active_file="tool.py",
            selection=None,
            cursor=None,
            virtual_files=virtual_files,
            ops=ops,
        ),
    )

    applied = await apply_handler.handle(
        actor=actor,
        command=EditOpsApplyCommand(
            tool_id=tool_id,
            active_file="tool.py",
            selection=None,
            cursor=None,
            virtual_files=virtual_files,
            ops=ops,
            base_hash=preview.meta.base_hash,
            patch_id=preview.meta.patch_id,
        ),
    )

    assert applied.ok is True
    assert applied.after_virtual_files["tool.py"] == "print('bye')\n"
