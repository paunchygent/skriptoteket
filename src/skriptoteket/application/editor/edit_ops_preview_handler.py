from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable

import structlog

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.role_guards import require_at_least_role
from skriptoteket.protocols.editor_patches import UnifiedDiffApplierProtocol
from skriptoteket.protocols.llm import (
    EditOpsApplyCommand,
    EditOpsApplyHandlerProtocol,
    EditOpsCursor,
    EditOpsOp,
    EditOpsPreviewCommand,
    EditOpsPreviewErrorDetails,
    EditOpsPreviewHandlerProtocol,
    EditOpsPreviewMeta,
    EditOpsPreviewResult,
    EditOpsSelection,
    VirtualFileId,
)

logger = structlog.get_logger(__name__)

_MAX_FUZZ_DEFAULT = 2
_MAX_OFFSET_LINES_DEFAULT = 50

_PATCH_MIX_ERROR = "AI-förslaget blandar patch med andra ändringar i samma fil. Regenerera."
_PATCH_MULTIPLE_ERROR = "AI-förslaget innehåller flera patchar för samma fil. Regenerera."


def _sha256(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


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
    non_patch_files: set[VirtualFileId] = set()
    for op in ops:
        if op.op == "patch":
            patch_counts[op.target_file] = patch_counts.get(op.target_file, 0) + 1
        else:
            non_patch_files.add(op.target_file)
    for file_id, count in patch_counts.items():
        if count > 1:
            return _PATCH_MULTIPLE_ERROR
        if file_id in non_patch_files:
            return _PATCH_MIX_ERROR
    return None


def _resolve_anchor(text: str, match: str) -> tuple[int, int] | None:
    if not match:
        return None
    start = text.find(match)
    if start == -1:
        return None
    second = text.find(match, start + len(match))
    if second != -1:
        return None
    return start, start + len(match)


def _apply_insert(
    *,
    file_id: VirtualFileId,
    current: str,
    op: EditOpsOp,
    selection: EditOpsSelection | None,
    cursor: EditOpsCursor | None,
    active_file: VirtualFileId,
) -> tuple[str | None, str | None]:
    if op.op != "insert":
        return None, "Internal error: op mismatch"
    if not op.content:
        return None, "AI-förslaget saknar innehåll för insert."

    target = op.target
    if target.kind == "cursor":
        if cursor is None:
            return None, "AI-förslaget använder markör men ingen markör finns."
        if file_id != active_file:
            return None, "AI-förslaget använder markör i en annan fil än den aktiva."
        if cursor.pos < 0 or cursor.pos > len(current):
            return None, "AI-förslagets markör matchar inte filens innehåll."
        return current[: cursor.pos] + op.content + current[cursor.pos :], None

    if target.kind == "anchor":
        resolved = _resolve_anchor(current, target.anchor.match)
        if resolved is None:
            return None, "AI-förslaget hittade inte ankaret i filen. Regenerera."
        start, end = resolved
        if target.anchor.placement is None:
            return None, "AI-förslaget saknar placering för ankaret."
        insert_at = start if target.anchor.placement == "before" else end
        return current[:insert_at] + op.content + current[insert_at:], None

    return None, f"AI-förslaget använder insert med {target.kind}-mål som inte stöds."


def _apply_replace(
    *,
    file_id: VirtualFileId,
    current: str,
    op: EditOpsOp,
    selection: EditOpsSelection | None,
    cursor: EditOpsCursor | None,
    active_file: VirtualFileId,
) -> tuple[str | None, str | None]:
    if op.op != "replace":
        return None, "Internal error: op mismatch"
    if not op.content:
        return None, "AI-förslaget saknar innehåll för replace."

    target = op.target
    if target.kind == "selection":
        if selection is None:
            return None, "AI-förslaget använder markering men ingen markering finns."
        if file_id != active_file:
            return None, "AI-förslaget använder markering i en annan fil än den aktiva."
        if selection.start < 0 or selection.end < 0 or selection.end < selection.start:
            return None, "AI-förslagets markering matchar inte filens innehåll."
        if selection.end > len(current):
            return None, "AI-förslagets markering matchar inte filens innehåll."
        return current[: selection.start] + op.content + current[selection.end :], None

    if target.kind == "document":
        return op.content, None

    if target.kind == "anchor":
        resolved = _resolve_anchor(current, target.anchor.match)
        if resolved is None:
            return None, "AI-förslaget hittade inte ankaret i filen. Regenerera."
        start, end = resolved
        return current[:start] + op.content + current[end:], None

    if target.kind == "cursor":
        return None, "AI-förslaget använder replace med cursor-mål som inte stöds."

    return None, "AI-förslaget kunde inte tolkas."


def _apply_delete(
    *,
    file_id: VirtualFileId,
    current: str,
    op: EditOpsOp,
    selection: EditOpsSelection | None,
    cursor: EditOpsCursor | None,
    active_file: VirtualFileId,
) -> tuple[str | None, str | None]:
    if op.op != "delete":
        return None, "Internal error: op mismatch"

    if getattr(op, "content", None) is not None:
        return None, "AI-förslaget skickade innehåll för delete."

    target = op.target
    if target.kind == "selection":
        if selection is None:
            return None, "AI-förslaget använder markering men ingen markering finns."
        if file_id != active_file:
            return None, "AI-förslaget använder markering i en annan fil än den aktiva."
        if selection.start < 0 or selection.end < 0 or selection.end < selection.start:
            return None, "AI-förslagets markering matchar inte filens innehåll."
        if selection.end > len(current):
            return None, "AI-förslagets markering matchar inte filens innehåll."
        return current[: selection.start] + current[selection.end :], None

    if target.kind == "document":
        return "", None

    if target.kind == "anchor":
        resolved = _resolve_anchor(current, target.anchor.match)
        if resolved is None:
            return None, "AI-förslaget hittade inte ankaret i filen. Regenerera."
        start, end = resolved
        return current[:start] + current[end:], None

    if target.kind == "cursor":
        return None, "AI-förslaget använder delete med cursor-mål som inte stöds."

    return None, "AI-förslaget kunde inte tolkas."


class EditOpsPreviewHandler(EditOpsPreviewHandlerProtocol):
    def __init__(self, *, patch_applier: UnifiedDiffApplierProtocol) -> None:
        self._patch_applier = patch_applier

    async def handle(self, *, actor: User, command: EditOpsPreviewCommand) -> EditOpsPreviewResult:
        require_at_least_role(user=actor, role=Role.CONTRIBUTOR)

        coherency_error = _validate_patch_coherency(command.ops)
        targets = _target_files(command.ops)
        base_hash = (
            _compute_base_hash(virtual_files=command.virtual_files, targets=targets)
            if targets
            else _sha256("")
        )

        if coherency_error:
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

        normalized_ops_for_id: list[dict[str, object]] = []

        for index, op in enumerate(command.ops):
            file_id = op.target_file
            current = next_files[file_id]

            if op.op == "patch":
                try:
                    prepared = self._patch_applier.prepare(
                        target_file=file_id, unified_diff=op.patch
                    )
                except ValueError as exc:
                    errors.append(str(exc))
                    error_details.append(
                        EditOpsPreviewErrorDetails(op_index=index, target_file=file_id)
                    )
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
                    break

                next_files[file_id] = result.next_text
                if result.meta is not None:
                    fuzz_level_used = max(fuzz_level_used, result.meta.fuzz_level_used)
                    max_offset = max(max_offset, result.meta.max_offset)
                    applied_cleanly = applied_cleanly and result.meta.applied_cleanly
                continue

            # CRUD ops
            payload = op.model_dump(exclude_none=True)
            normalized_ops_for_id.append(payload)

            if op.op == "insert":
                updated, err = _apply_insert(
                    file_id=file_id,
                    current=current,
                    op=op,
                    selection=command.selection,
                    cursor=command.cursor,
                    active_file=command.active_file,
                )
            elif op.op == "replace":
                updated, err = _apply_replace(
                    file_id=file_id,
                    current=current,
                    op=op,
                    selection=command.selection,
                    cursor=command.cursor,
                    active_file=command.active_file,
                )
            elif op.op == "delete":
                updated, err = _apply_delete(
                    file_id=file_id,
                    current=current,
                    op=op,
                    selection=command.selection,
                    cursor=command.cursor,
                    active_file=command.active_file,
                )
            else:
                updated, err = None, "AI-förslaget har en okänd operation."

            if err:
                errors.append(err)
                error_details.append(
                    EditOpsPreviewErrorDetails(op_index=index, target_file=file_id)
                )
                break
            if updated is not None:
                next_files[file_id] = updated

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
