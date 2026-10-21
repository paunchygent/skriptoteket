"""Shared editor payload preparation and conversion-placeholder invariants."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from uuid import UUID

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJobStatus,
    ExamWorkspaceConversionJobView,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_conversion_merge import (
    ConversionProgress,
    changed_placeholders,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_document_store import (
    ExamWorkspaceDocumentStore,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_item_support import (
    picture_media_type,
)
from skriptoteket.domain.curated_apps.exam_workspace.container import ExamWorkspaceContainerContent
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import NativeExamDocument
from skriptoteket.domain.errors import DomainError, ErrorCode, validation_error
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.vault import VaultFile
from skriptoteket.protocols.exam_workspace import ExamWorkspaceContainerCodecProtocol
from skriptoteket.protocols.vault import VaultFileRepositoryProtocol


async def prepare_editor_content(
    *,
    actor: User,
    lineage_id: UUID,
    document: NativeExamDocument,
    vault_files: VaultFileRepositoryProtocol,
    codec: ExamWorkspaceContainerCodecProtocol,
    store: ExamWorkspaceDocumentStore,
    new_assets_by_id: Mapping[str, bytes] | None = None,
) -> tuple[VaultFile, ExamWorkspaceContainerContent, bytes]:
    """Build the exam file for `document`, taking its pictures from the saved file, the
    history, or `new_assets_by_id` (bytes the editor sends once for a picture it added)."""
    head = await vault_files.get_document_head(user_id=actor.id, document_lineage_id=lineage_id)
    if head is None:
        raise DomainError(code=ErrorCode.NOT_FOUND, message="Provdokumentet finns inte.")
    if document.document_id != lineage_id:
        raise validation_error("Dokumentets identitet matchar inte adressen.")
    new_assets_by_id = new_assets_by_id or {}
    declared = {asset.asset_id: asset for asset in document.assets}
    for asset_id, payload in new_assets_by_id.items():
        asset = declared.get(asset_id)
        if (
            asset is None
            or asset_id != f"asset_{asset.sha256[:16]}"
            or hashlib.sha256(payload).hexdigest() != asset.sha256
            or len(payload) != asset.byte_length
            or picture_media_type(payload) != asset.media_type
        ):
            raise validation_error("Bilden kunde inte sparas.", details={"asset_id": asset_id})
    saved = codec.parse(content=await store.load(actor=actor, vault_file=head))
    if saved.document.document_id != lineage_id or saved.document.revision != head.document_version:
        raise validation_error("Den sparade dokumentversionen är skadad.")
    assets = dict(saved.assets_by_id)
    assets.update(
        {
            asset_id: payload
            for asset_id, payload in new_assets_by_id.items()
            if asset_id not in assets
        }
    )
    wanted = tuple(
        sorted(
            {asset.asset_id for asset in document.assets} - assets.keys(),
        )
    )
    if wanted:
        assets.update(
            await vault_files.get_history_assets(
                user_id=actor.id, document_lineage_id=lineage_id, asset_ids=wanted
            )
        )
    missing = {asset.asset_id for asset in document.assets} - assets.keys()
    if missing:
        raise validation_error(
            "Dokumentet hänvisar till bilder som saknas.",
            details={"missing_assets": sorted(missing)},
        )
    content = codec.build(
        content=ExamWorkspaceContainerContent(
            document=document,
            notes=saved.notes,
            assets_by_id={asset.asset_id: assets[asset.asset_id] for asset in document.assets},
        )
    )
    store.validate_size(content)
    return head, saved, content


def refuse_placeholder_changes(
    *,
    job: ExamWorkspaceConversionJobView | None,
    base: NativeExamDocument,
    saved: NativeExamDocument,
) -> None:
    if job is None or job.status not in (
        ExamAnswerKeyEnrichmentJobStatus.QUEUED,
        ExamAnswerKeyEnrichmentJobStatus.RUNNING,
    ):
        return
    progress = ConversionProgress.model_validate(job.conversion_progress or {})
    if (progress.revision or 0) > base.revision:
        raise DomainError(
            code=ErrorCode.CONFLICT,
            message="Dokumentet har ändrats sedan det öppnades.",
            details={"expected_revision": base.revision, "current_revision": progress.revision},
        )
    changed = changed_placeholders(progress=progress, base=base, saved=saved)
    if changed:
        raise DomainError(
            code=ErrorCode.CONVERSION_IN_PROGRESS,
            message="Provet kunde inte sparas. Vänta tills frågorna har konverterats "
            "innan du ändrar, flyttar eller tar bort dem.",
            details={"item_ids": changed},
        )
