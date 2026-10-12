"""Exam workspace document handlers: DOCX import, reopen, and versioned save.

The native exam document persists as one immutable Mina filer container per
revision (D2/S3). Version numbers advance under the per-user vault usage
lock, with the partial unique index on (user, lineage, version) as the
database backstop; a stale ``expected_revision`` maps to CONFLICT exactly
like the correction-session precedent.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.exc import IntegrityError

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJob,
    ExamAnswerKeyEnrichmentJobStatus,
    ExamAnswerKeySourceKind,
    ExamWorkspaceConversionJobView,
)
from skriptoteket.application.curated_apps.exam_workspace import (
    ExamWorkspaceConversionStatus,
    ExamWorkspaceConversionUnit,
    ExamWorkspaceDocumentListResponse,
    ExamWorkspaceDocumentResponse,
    ExamWorkspaceDocumentSummary,
    SaveExamWorkspaceDocumentRequest,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_conversion_merge import (
    ConversionProgress,
    changed_placeholders,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_proposal_carry_forward import (
    CarryExamWorkspaceProposals,
)
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.exam_workspace.container import (
    ExamWorkspaceContainerContent,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.errors import DomainError, ErrorCode, validation_error
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.input_files import sanitize_input_filename
from skriptoteket.domain.scripting.vault import VaultFile, VaultFileSourceKind, VaultUsage
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.exam_answer_key import ExamAnswerKeyEnrichmentJobRepositoryProtocol
from skriptoteket.protocols.exam_workspace import (
    ExamWorkspaceContainerCodecProtocol,
)
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from skriptoteket.protocols.vault import (
    VaultFileRepositoryProtocol,
    VaultStorageProtocol,
    VaultUsageRepositoryProtocol,
)

EXAM_WORKSPACE_SOURCE_ARTIFACT_PREFIX = "documents.conversion_hub:exam-workspace"
_UNFINISHED = (ExamAnswerKeyEnrichmentJobStatus.QUEUED, ExamAnswerKeyEnrichmentJobStatus.RUNNING)


def _document_not_found(lineage_id: UUID) -> DomainError:
    return DomainError(
        code=ErrorCode.NOT_FOUND,
        message="Provdokumentet finns inte.",
        details={"lineage_id": str(lineage_id)},
    )


class ExamWorkspaceDocumentStore:
    """Persist and load versioned exam workspace containers in Mina filer."""

    def __init__(
        self,
        *,
        vault_files: VaultFileRepositoryProtocol,
        vault_usage: VaultUsageRepositoryProtocol,
        vault_storage: VaultStorageProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        settings: Settings,
        proposal_carry_forward: CarryExamWorkspaceProposals,
    ) -> None:
        self._vault_files = vault_files
        self._vault_usage = vault_usage
        self._vault_storage = vault_storage
        self._uow = uow
        self._clock = clock
        self._settings = settings
        self._proposal_carry_forward = proposal_carry_forward

    async def save_version(
        self,
        *,
        actor: User,
        file_id: UUID,
        name: str,
        content: bytes,
        lineage_id: UUID,
        version: int,
        previous_document: NativeExamDocument | None = None,
        document: NativeExamDocument | None = None,
        rejected_proposal_item_ids: tuple[str, ...] = (),
    ) -> VaultFile:
        actual_bytes = len(content)
        if actual_bytes <= 0:
            raise validation_error("Dokumentet saknar innehåll.")
        if actual_bytes > self._settings.VAULT_MAX_FILE_BYTES:
            raise validation_error(
                "Dokumentet är större än maxstorleken för Mina filer.",
                details={
                    "bytes": actual_bytes,
                    "max_bytes": self._settings.VAULT_MAX_FILE_BYTES,
                },
            )

        now = self._clock.now()
        stored = False
        try:
            async with self._uow:
                usage = await self._vault_usage.get_for_update(user_id=actor.id, now=now)
                if usage.bytes_total + actual_bytes > self._settings.VAULT_MAX_TOTAL_BYTES:
                    raise validation_error(
                        "Mina filer är fullt; ta bort filer och försök igen.",
                        details={
                            "bytes_total": usage.bytes_total,
                            "attempted_bytes": actual_bytes,
                            "max_total_bytes": self._settings.VAULT_MAX_TOTAL_BYTES,
                        },
                    )
                vault_file = await self._vault_files.create(
                    file=VaultFile(
                        id=file_id,
                        user_id=actor.id,
                        name=name,
                        bytes=actual_bytes,
                        source_kind=VaultFileSourceKind.APP_EXPORT,
                        source_run_id=None,
                        source_artifact_id=(
                            f"{EXAM_WORKSPACE_SOURCE_ARTIFACT_PREFIX}:{lineage_id}:v{version}"
                        ),
                        document_lineage_id=lineage_id,
                        document_version=version,
                        created_at=now,
                        deleted_at=None,
                    )
                )
                await self._vault_storage.store_file(
                    user_id=actor.id, file_id=vault_file.id, content=content
                )
                stored = True
                await self._vault_usage.upsert(
                    usage=VaultUsage(
                        user_id=actor.id,
                        bytes_total=usage.bytes_total + actual_bytes,
                        updated_at=now,
                    )
                )
                if previous_document is not None and document is not None:
                    await self._proposal_carry_forward.carry(
                        owner_user_id=actor.id,
                        previous_document=previous_document,
                        document=document,
                        rejected_item_ids=frozenset(rejected_proposal_item_ids),
                    )
        except IntegrityError as error:
            if stored:
                await self.discard_version_file(actor=actor, file_id=file_id)
            raise DomainError(
                code=ErrorCode.CONFLICT,
                message="Dokumentet sparades samtidigt i en annan flik.",
                details={"lineage_id": str(lineage_id), "version": version},
            ) from error
        except Exception:
            if stored:
                await self.discard_version_file(actor=actor, file_id=file_id)
            raise
        return vault_file

    async def retire_version(self, *, actor: User, retired: VaultFile) -> None:
        """Soft-delete one superseded revision and release its bytes from vault usage.

        Runs inside the caller's unit of work; the stored payload expires with the row.
        """
        now = self._clock.now()
        await self._vault_files.update(file=retired.model_copy(update={"deleted_at": now}))
        usage = await self._vault_usage.get_for_update(user_id=actor.id, now=now)
        await self._vault_usage.upsert(
            usage=VaultUsage(
                user_id=actor.id,
                bytes_total=max(0, usage.bytes_total - retired.bytes),
                updated_at=now,
            )
        )

    async def discard_version_file(self, *, actor: User, file_id: UUID) -> None:
        await self._vault_storage.delete_file(user_id=actor.id, file_id=file_id)

    async def load_version(self, *, actor: User, vault_file: VaultFile) -> bytes:
        return await self._vault_storage.read_file(user_id=actor.id, file_id=vault_file.id)


def _summary(vault_file: VaultFile) -> ExamWorkspaceDocumentSummary:
    assert vault_file.document_lineage_id is not None
    assert vault_file.document_version is not None
    return ExamWorkspaceDocumentSummary(
        lineage_id=vault_file.document_lineage_id,
        version=vault_file.document_version,
        vault_file_id=vault_file.id,
        name=vault_file.name,
        saved_at=vault_file.created_at,
    )


class ImportExamWorkspaceDocumentHandler:
    """Import one teacher DOCX into a new versioned exam workspace document."""

    def __init__(
        self,
        *,
        jobs: ExamAnswerKeyEnrichmentJobRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        settings: Settings,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._jobs = jobs
        self._uow = uow
        self._clock = clock
        self._settings = settings
        self._id_generator = id_generator

    async def handle(
        self, *, actor: User, filename: str, content: bytes
    ) -> ExamWorkspaceConversionStatus:
        safe_name = sanitize_input_filename(input_filename=filename)
        if not safe_name.lower().endswith(".docx"):
            raise validation_error("Välj en .docx-fil.", details={"filename": safe_name})
        if not content:
            raise validation_error("Filen saknar innehåll.")
        if len(content) > self._settings.VAULT_MAX_FILE_BYTES:
            raise validation_error("Word-dokumentet är större än maxstorleken för Mina filer.")

        document_id = self._id_generator.new_uuid()
        now = self._clock.now()
        async with self._uow:
            job = await self._jobs.create(
                job=ExamAnswerKeyEnrichmentJob(
                    id=self._id_generator.new_uuid(),
                    source_kind=ExamAnswerKeySourceKind.DOCX_IMPORT,
                    owner_user_id=actor.id,
                    status=ExamAnswerKeyEnrichmentJobStatus.QUEUED,
                    input_filename=safe_name,
                    source_docx=content,
                    workspace_lineage_id=document_id,
                    workspace_document_revision=1,
                    available_at=now,
                    created_at=now,
                    updated_at=now,
                )
            )
        return conversion_status(
            ExamWorkspaceConversionJobView.model_validate(job, from_attributes=True)
        )


def conversion_status(job: ExamWorkspaceConversionJobView) -> ExamWorkspaceConversionStatus:
    assert job.workspace_lineage_id is not None
    progress = ConversionProgress.model_validate(job.conversion_progress or {})
    return ExamWorkspaceConversionStatus(
        job_id=job.id,
        lineage_id=job.workspace_lineage_id,
        state=job.status.value,
        error_message=job.last_error
        if job.status is ExamAnswerKeyEnrichmentJobStatus.FAILED
        else None,
        document_revision=progress.revision,
        questions_total=progress.questions_total,
        questions_done=progress.questions_done,
        units=tuple(
            ExamWorkspaceConversionUnit(
                unit_id=unit.unit_id,
                question=unit.question,
                state=unit.state.value,
                item_ids=unit.item_ids,
            )
            for unit in progress.units
            if unit.digest is not None
        ),
    )


class GetExamWorkspaceConversionStatusHandler:
    """Read one actor-owned background conversion without exposing source bytes."""

    def __init__(self, *, jobs: ExamAnswerKeyEnrichmentJobRepositoryProtocol) -> None:
        self._jobs = jobs

    async def handle(self, *, actor: User, job_id: UUID) -> ExamWorkspaceConversionStatus:
        job = await self._jobs.get_conversion_view(job_id=job_id)
        if (
            job is None
            or job.owner_user_id != actor.id
            or job.source_kind is not ExamAnswerKeySourceKind.DOCX_IMPORT
        ):
            raise DomainError(code=ErrorCode.NOT_FOUND, message="Konverteringen finns inte.")
        return conversion_status(job)


class GetExamWorkspaceDocumentHandler:
    """Reopen the head version of an exam workspace document."""

    def __init__(
        self,
        *,
        vault_files: VaultFileRepositoryProtocol,
        codec: ExamWorkspaceContainerCodecProtocol,
        store: ExamWorkspaceDocumentStore,
        jobs: ExamAnswerKeyEnrichmentJobRepositoryProtocol,
        uow: UnitOfWorkProtocol,
    ) -> None:
        self._vault_files = vault_files
        self._codec = codec
        self._store = store
        self._jobs = jobs
        self._uow = uow

    async def handle(self, *, actor: User, lineage_id: UUID) -> ExamWorkspaceDocumentResponse:
        # The job lock holds conversion back, so the head matches the conversion's units.
        async with self._uow:
            job = await self._jobs.lock_conversion_view_by_lineage(
                owner_user_id=actor.id, workspace_lineage_id=lineage_id
            )
            head = await self._vault_files.get_document_head(
                user_id=actor.id, document_lineage_id=lineage_id
            )
            if head is None:
                raise _document_not_found(lineage_id)
            content = await self._store.load_version(actor=actor, vault_file=head)
        container = self._codec.parse(content=content)
        if (
            container.document.document_id != lineage_id
            or container.document.revision != head.document_version
        ):
            raise validation_error(
                "Den sparade dokumentversionen är skadad.",
                details={"lineage_id": str(lineage_id)},
            )
        return ExamWorkspaceDocumentResponse(
            document=container.document,
            summary=_summary(head),
            notes=container.notes,
            conversion=None if job is None else conversion_status(job),
        )


class ListExamWorkspaceDocumentsHandler:
    """List the actor's workspace documents as head-version summaries."""

    def __init__(self, *, vault_files: VaultFileRepositoryProtocol) -> None:
        self._vault_files = vault_files

    async def handle(self, *, actor: User) -> ExamWorkspaceDocumentListResponse:
        heads = await self._vault_files.list_document_heads(
            user_id=actor.id,
            source_artifact_prefix=f"{EXAM_WORKSPACE_SOURCE_ARTIFACT_PREFIX}:",
        )
        return ExamWorkspaceDocumentListResponse(documents=tuple(_summary(head) for head in heads))


class SaveExamWorkspaceDocumentHandler:
    """Save a new document revision guarded by expected_revision (CONFLICT on stale)."""

    def __init__(
        self,
        *,
        vault_files: VaultFileRepositoryProtocol,
        codec: ExamWorkspaceContainerCodecProtocol,
        store: ExamWorkspaceDocumentStore,
        id_generator: IdGeneratorProtocol,
        jobs: ExamAnswerKeyEnrichmentJobRepositoryProtocol,
    ) -> None:
        self._vault_files = vault_files
        self._codec = codec
        self._store = store
        self._id_generator = id_generator
        self._jobs = jobs

    async def handle(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        request: SaveExamWorkspaceDocumentRequest,
    ) -> ExamWorkspaceDocumentResponse:
        head = await self._vault_files.get_document_head(
            user_id=actor.id, document_lineage_id=lineage_id
        )
        if head is None:
            raise _document_not_found(lineage_id)
        if head.document_version != request.expected_revision:
            raise DomainError(
                code=ErrorCode.CONFLICT,
                message="Dokumentet har ändrats sedan det öppnades.",
                details={
                    "expected_revision": request.expected_revision,
                    "current_revision": head.document_version,
                },
            )
        document = request.document
        if document.document_id != lineage_id:
            raise validation_error(
                "Dokumentets identitet matchar inte adressen.",
                details={"lineage_id": str(lineage_id)},
            )
        if document.revision != request.expected_revision + 1:
            raise validation_error(
                "Dokumentversionen måste öka med exakt ett vid sparande.",
                details={
                    "expected_revision": request.expected_revision,
                    "document_revision": document.revision,
                },
            )

        head_content = await self._store.load_version(actor=actor, vault_file=head)
        head_container = self._codec.parse(content=head_content)
        if (
            head_container.document.document_id != lineage_id
            or head_container.document.revision != request.expected_revision
        ):
            raise validation_error("Den sparade dokumentversionen är skadad.")
        job = await self._jobs.lock_conversion_view_by_lineage(
            owner_user_id=actor.id, workspace_lineage_id=lineage_id
        )
        self._refuse_placeholder_changes(job=job, base=head_container.document, saved=document)
        assets_by_id: dict[str, bytes] = {}
        if document.assets:
            missing = {
                asset.asset_id
                for asset in document.assets
                if asset.asset_id not in head_container.assets_by_id
            }
            if missing:
                raise validation_error(
                    "Dokumentet hänvisar till bilder som saknas.",
                    details={"missing_assets": sorted(missing)},
                )
            assets_by_id = {
                asset.asset_id: head_container.assets_by_id[asset.asset_id]
                for asset in document.assets
            }

        container_bytes = self._codec.build(
            content=ExamWorkspaceContainerContent(
                document=document,
                assets_by_id=assets_by_id,
                notes=head_container.notes,
            )
        )
        vault_file = await self._store.save_version(
            actor=actor,
            file_id=self._id_generator.new_uuid(),
            name=head.name,
            content=container_bytes,
            lineage_id=lineage_id,
            version=document.revision,
            previous_document=head_container.document,
            document=document,
            rejected_proposal_item_ids=request.rejected_proposal_item_ids,
        )
        return ExamWorkspaceDocumentResponse(
            document=document,
            summary=_summary(vault_file),
            notes=head_container.notes,
            conversion=None if job is None else conversion_status(job),
        )

    @staticmethod
    def _refuse_placeholder_changes(
        *,
        job: ExamWorkspaceConversionJobView | None,
        base: NativeExamDocument,
        saved: NativeExamDocument,
    ) -> None:
        """While conversion runs, a save keeps every placeholder of its base as it is (D30)."""
        if job is None or job.status not in _UNFINISHED:
            return
        progress = ConversionProgress.model_validate(job.conversion_progress or {})
        if (progress.revision or 0) > base.revision:
            raise DomainError(
                code=ErrorCode.CONFLICT,
                message="Dokumentet har ändrats sedan det öppnades.",
                details={
                    "expected_revision": base.revision,
                    "current_revision": progress.revision,
                },
            )
        changed = changed_placeholders(progress=progress, base=base, saved=saved)
        if changed:
            raise validation_error(
                "Provet sparades inte: frågor som fortfarande konverteras går inte att ändra, "
                "flytta eller ta bort förrän de är klara.",
                details={"item_ids": changed},
            )
