"""Stateless public rendering for guest exam workspace exports.

Purpose:
  Verify that a guest-supplied document and its picture bytes describe the same
  assets the document declares, then render through the signed-in export
  renderer. Nothing is stored and no actor is involved.

Relationships:
  - Uses ``ExamWorkspaceExportRenderer`` for QTI, PDF, DOCX and the checklist.
  - Called by the public exam workspace routes after database admission.
  - Mirrors ``ExamWorkspaceContainerContent``'s asset declaration checks.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping

from skriptoteket.application.curated_apps.exam_workspace import (
    ExamWorkspaceExportChecklistResponse,
    ExamWorkspaceExportFile,
    ExamWorkspaceExportTarget,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_export_renderer import (
    ExamWorkspaceExportRenderer,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.errors import DomainError, ErrorCode

_MISMATCH_MESSAGE = "En bild matchar inte provets deklaration."


def asset_mismatch_error(asset_id: str) -> DomainError:
    """One declared asset and its supplied bytes disagree."""

    return DomainError(
        code=ErrorCode.VALIDATION_ERROR,
        message=_MISMATCH_MESSAGE,
        details={"reason": "asset_mismatch", "asset_id": asset_id},
    )


class PublicExamWorkspaceExportHandler:
    """Render guest export files only from bytes that match the document declarations."""

    def __init__(self, *, renderer: ExamWorkspaceExportRenderer) -> None:
        self._renderer = renderer

    def render(
        self,
        *,
        document: NativeExamDocument,
        assets_by_id: Mapping[str, bytes],
        target: ExamWorkspaceExportTarget,
    ) -> ExamWorkspaceExportFile:
        self._require_declared_assets(document=document, assets_by_id=assets_by_id)
        return self._renderer.render(
            document=document,
            assets_by_id=assets_by_id,
            target=target,
        )

    def checklist(
        self,
        *,
        document: NativeExamDocument,
        assets_by_id: Mapping[str, bytes],
    ) -> ExamWorkspaceExportChecklistResponse:
        self._require_declared_assets(document=document, assets_by_id=assets_by_id)
        return self._renderer.checklist(
            document=document,
            assets_by_id=assets_by_id,
        )

    @staticmethod
    def _require_declared_assets(
        *,
        document: NativeExamDocument,
        assets_by_id: Mapping[str, bytes],
    ) -> None:
        declared = {asset.asset_id: asset for asset in document.assets}
        provided = set(assets_by_id)
        extra = sorted(provided - set(declared))
        if extra:
            raise asset_mismatch_error(extra[0])
        missing = sorted(set(declared) - provided)
        if missing:
            raise asset_mismatch_error(missing[0])
        for asset in document.assets:
            payload = assets_by_id[asset.asset_id]
            if len(payload) != asset.byte_length:
                raise asset_mismatch_error(asset.asset_id)
            if hashlib.sha256(payload).hexdigest() != asset.sha256:
                raise asset_mismatch_error(asset.asset_id)
