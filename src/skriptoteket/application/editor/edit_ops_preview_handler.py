from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Iterable
from uuid import UUID

import structlog
from structlog.contextvars import get_contextvars

from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.role_guards import require_at_least_role
from skriptoteket.protocols.editor_patches import UnifiedDiffApplierProtocol
from skriptoteket.protocols.llm import (
    EditOpsApplyCommand,
    EditOpsApplyHandlerProtocol,
    EditOpsOp,
    EditOpsPreviewCommand,
    EditOpsPreviewErrorDetails,
    EditOpsPreviewHandlerProtocol,
    EditOpsPreviewMeta,
    EditOpsPreviewResult,
    VirtualFileId,
)
from skriptoteket.protocols.llm_captures import LlmCaptureStoreProtocol

logger = structlog.get_logger(__name__)

_MAX_FUZZ_DEFAULT = 2
_MAX_OFFSET_LINES_DEFAULT = 50

_PATCH_MULTIPLE_ERROR = "AI-förslaget innehåller flera patchar för samma fil. Regenerera."


def _sha256(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _join_patch_lines(patch_lines: list[str]) -> str:
    patch = "\n".join(patch_lines)
    if not patch.endswith("\n"):
        patch += "\n"
    return patch


def _target_files(ops: Iterable[EditOpsOp]) -> list[VirtualFileId]:
    seen: set[VirtualFileId] = set()
    ordered: list[VirtualFileId] = []
    for op in ops:
        if op.target_file not in seen:
            seen.add(op.target_file)
            ordered.append(op.target_file)
    return ordered


def _compute_base_hash(
    *, virtual_files: dict[VirtualFileId, str], targets: list[VirtualFileId]
) -> str:
    payload = "\u0000".join([f"{file_id}\u0000{virtual_files[file_id]}" for file_id in targets])
    return _sha256(payload)


def _validate_patch_coherency(ops: list[EditOpsOp]) -> str | None:
    patch_counts: dict[VirtualFileId, int] = {}
    for op in ops:
        patch_counts[op.target_file] = patch_counts.get(op.target_file, 0) + 1
    for file_id, count in patch_counts.items():
        if count > 1:
            return _PATCH_MULTIPLE_ERROR
    return None


class EditOpsPreviewHandler(EditOpsPreviewHandlerProtocol):
    def __init__(
        self,
        *,
        settings: Settings,
        capture_store: LlmCaptureStoreProtocol,
        patch_applier: UnifiedDiffApplierProtocol,
    ) -> None:
        self._settings = settings
        self._capture_store = capture_store
        self._patch_applier = patch_applier

    async def handle(self, *, actor: User, command: EditOpsPreviewCommand) -> EditOpsPreviewResult:
        require_at_least_role(user=actor, role=Role.CONTRIBUTOR)
        started_at = time.monotonic()
        raw_correlation_id = get_contextvars().get("correlation_id")
        capture_id = None
        if isinstance(raw_correlation_id, str) and raw_correlation_id:
            try:
                capture_id = UUID(raw_correlation_id)
            except ValueError:
                capture_id = None

        coherency_error = _validate_patch_coherency(command.ops)
        targets = _target_files(command.ops)
        base_hash = (
            _compute_base_hash(virtual_files=command.virtual_files, targets=targets)
            if targets
            else _sha256("")
        )

        if coherency_error:
            logger.info(
                "edit_ops_preview",
                user_id=str(actor.id),
                tool_id=str(command.tool_id),
                op_count=len(command.ops),
                ok=False,
                fuzz_level_used=0,
                max_offset=0,
                error_kind="coherency_error",
                failed_op_index=None,
                target_file=None,
            )
            if self._settings.LLM_CAPTURE_ON_ERROR_ENABLED and capture_id is not None:
                await self._capture_store.write_capture(
                    kind="edit_ops_preview_failure",
                    capture_id=capture_id,
                    payload={
                        "outcome": "coherency_error",
                        "user_id": str(actor.id),
                        "tool_id": str(command.tool_id),
                        "active_file": command.active_file,
                        "op_count": len(command.ops),
                        "error_kind": "coherency_error",
                        "failed_op_index": None,
                        "target_file": None,
                        "errors": [coherency_error],
                        "error_details": [],
                        "ops": [op.model_dump(exclude_none=True) for op in command.ops],
                        "base_hash": base_hash,
                        "elapsed_ms": int((time.monotonic() - started_at) * 1000),
                    },
                )
            return EditOpsPreviewResult(
                ok=False,
                after_virtual_files=dict(command.virtual_files),
                errors=[coherency_error],
                meta=EditOpsPreviewMeta(
                    base_hash=base_hash,
                    patch_id=_sha256("invalid"),
                    requires_confirmation=False,
                    applied_cleanly=False,
                ),
            )

        next_files: dict[VirtualFileId, str] = dict(command.virtual_files)
        errors: list[str] = []
        error_details: list[EditOpsPreviewErrorDetails] = []
        normalizations: list[str] = []
        fuzz_level_used = 0
        max_offset = 0
        applied_cleanly = True

        error_kind: str | None = None
        failed_op_index: int | None = None
        failed_target_file: VirtualFileId | None = None

        normalized_ops_for_id: list[dict[str, object]] = []

        for index, op in enumerate(command.ops):
            file_id = op.target_file
            current = next_files[file_id]

            if op.op == "patch":
                try:
                    prepared = self._patch_applier.prepare(
                        target_file=file_id,
                        unified_diff=_join_patch_lines(op.patch_lines),
                        base_text=current,
                    )
                except ValueError as exc:
                    errors.append(str(exc))
                    error_details.append(
                        EditOpsPreviewErrorDetails(op_index=index, target_file=file_id)
                    )
                    error_kind = "patch_prepare_failed"
                    failed_op_index = index
                    failed_target_file = file_id
                    break

                normalized_ops_for_id.append(
                    {"op": "patch", "target_file": file_id, "patch_id": prepared.patch_id}
                )
                normalizations.extend(prepared.normalizations_applied)

                result = self._patch_applier.apply(
                    target_file=file_id,
                    base_text=current,
                    prepared=prepared,
                    max_fuzz=_MAX_FUZZ_DEFAULT,
                    max_offset_lines=_MAX_OFFSET_LINES_DEFAULT,
                    enable_whitespace_stage=True,
                )

                if not result.ok:
                    errors.append(result.error or "Patchen kunde inte appliceras. Regenerera.")
                    details = result.error_details
                    error_details.append(
                        EditOpsPreviewErrorDetails(
                            op_index=index,
                            target_file=file_id,
                            hunk_index=details.hunk_index if details else None,
                            hunk_header=details.hunk_header if details else None,
                            expected_snippet=details.expected_snippet if details else None,
                            base_snippet=details.base_snippet if details else None,
                        )
                    )
                    error_kind = "patch_apply_failed"
                    failed_op_index = index
                    failed_target_file = file_id
                    break

                next_files[file_id] = result.next_text
                if result.meta is not None:
                    fuzz_level_used = max(fuzz_level_used, result.meta.fuzz_level_used)
                    max_offset = max(max_offset, result.meta.max_offset)
                    applied_cleanly = applied_cleanly and result.meta.applied_cleanly
                continue

        patch_id_payload = json.dumps(
            normalized_ops_for_id,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        patch_id = _sha256(patch_id_payload)

        requires_confirmation = fuzz_level_used > 0 or max_offset > 10
        ok = len(errors) == 0
        if not ok:
            next_files = dict(command.virtual_files)

        logger.info(
            "edit_ops_preview",
            user_id=str(actor.id),
            tool_id=str(command.tool_id),
            op_count=len(command.ops),
            ok=ok,
            fuzz_level_used=fuzz_level_used,
            max_offset=max_offset,
            error_kind=error_kind,
            failed_op_index=failed_op_index,
            target_file=failed_target_file,
        )

        if not ok and self._settings.LLM_CAPTURE_ON_ERROR_ENABLED and capture_id is not None:
            await self._capture_store.write_capture(
                kind="edit_ops_preview_failure",
                capture_id=capture_id,
                payload={
                    "outcome": "preview_failed",
                    "user_id": str(actor.id),
                    "tool_id": str(command.tool_id),
                    "active_file": command.active_file,
                    "op_count": len(command.ops),
                    "error_kind": error_kind,
                    "failed_op_index": failed_op_index,
                    "target_file": failed_target_file,
                    "errors": errors,
                    "error_details": [item.model_dump(exclude_none=True) for item in error_details],
                    "ops": [op.model_dump(exclude_none=True) for op in command.ops],
                    "base_hash": base_hash,
                    "elapsed_ms": int((time.monotonic() - started_at) * 1000),
                },
            )

        return EditOpsPreviewResult(
            ok=ok,
            after_virtual_files=next_files,
            errors=errors,
            error_details=error_details,
            meta=EditOpsPreviewMeta(
                base_hash=base_hash,
                patch_id=patch_id,
                requires_confirmation=requires_confirmation,
                fuzz_level_used=fuzz_level_used,
                max_offset=max_offset,
                normalizations_applied=list(dict.fromkeys(normalizations)),
                applied_cleanly=applied_cleanly,
            ),
        )


class EditOpsApplyHandler(EditOpsApplyHandlerProtocol):
    def __init__(self, *, preview: EditOpsPreviewHandlerProtocol) -> None:
        self._preview = preview

    async def handle(self, *, actor: User, command: EditOpsApplyCommand) -> EditOpsPreviewResult:
        preview = await self._preview.handle(
            actor=actor,
            command=EditOpsPreviewCommand(
                tool_id=command.tool_id,
                active_file=command.active_file,
                selection=command.selection,
                cursor=command.cursor,
                virtual_files=command.virtual_files,
                ops=command.ops,
            ),
        )

        if preview.meta.base_hash != command.base_hash:
            raise DomainError(
                code=ErrorCode.CONFLICT,
                message=(
                    "Underlaget har ändrats sedan förhandsvisningen. "
                    "Uppdatera förhandsvisningen och bekräfta igen."
                ),
            )
        if preview.meta.patch_id != command.patch_id:
            raise DomainError(
                code=ErrorCode.CONFLICT,
                message=(
                    "Förhandsvisningen matchar inte längre förslaget. "
                    "Uppdatera förhandsvisningen och bekräfta igen."
                ),
            )
        return preview
