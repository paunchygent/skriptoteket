"""Shared editor payload preparation and conversion-placeholder invariants."""

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
) -> tuple[VaultFile, ExamWorkspaceContainerContent, bytes]:
    head = await vault_files.get_document_head(user_id=actor.id, document_lineage_id=lineage_id)
    if head is None:
        raise DomainError(code=ErrorCode.NOT_FOUND, message="Provdokumentet finns inte.")
    if document.document_id != lineage_id:
        raise validation_error("Dokumentets identitet matchar inte adressen.")
    saved = codec.parse(content=await store.load(actor=actor, vault_file=head))
    if saved.document.document_id != lineage_id or saved.document.revision != head.document_version:
        raise validation_error("Den sparade dokumentversionen är skadad.")
    assets = dict(saved.assets_by_id)
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
        raise validation_error(
            "Provet sparades inte: frågor som fortfarande konverteras går inte att ändra, "
            "flytta eller ta bort förrän de är klara.",
            details={"item_ids": changed},
        )
