"""Save converted batches as document revisions while a DOCX import runs (D25, D30).

The first admitted batch saves revision 1 with placeholders for the questions still
converting. Each later batch, the final document and a failed job's abandonment save
the next revision through ``merge_conversion``: each batch replaces its own placeholders,
and the teacher's edits on converted items stay. A conversion revision the teacher never
saved on is retired when conversion supersedes it, so intermediate revisions never
accumulate in the teacher's vault usage.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import PurePosixPath
from uuid import UUID

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJob,
    ExamAnswerKeyEnrichmentJobStatus,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_conversion_merge import (
    ConversionMerge,
    ConversionProgress,
    abandon_target,
    first_conversion,
    merge_conversion,
    target_from_update,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_document_store import (
    ExamWorkspaceDocumentStore,
)
from skriptoteket.domain.curated_apps.exam_workspace.container import (
    ExamWorkspaceContainerContent,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.vault import VaultFile
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.docx_conversion_progress import ConversionOutline, ConversionUpdate
from skriptoteket.protocols.exam_answer_key import ExamAnswerKeyEnrichmentJobRepositoryProtocol
from skriptoteket.protocols.exam_workspace import ExamWorkspaceContainerCodecProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.identity import UserRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from skriptoteket.protocols.vault import VaultFileRepositoryProtocol

_SAVE_ATTEMPTS = 3


def _referenced_payloads(
    document: NativeExamDocument, payloads: Mapping[str, bytes]
) -> dict[str, bytes]:
    """The payloads the document's own asset list references; a missing payload fails later
    in the container's fail-closed validation rather than being silently dropped."""
    return {
        asset.asset_id: payloads[asset.asset_id]
        for asset in document.assets
        if asset.asset_id in payloads
    }


def _version_name(job: ExamAnswerKeyEnrichmentJob, head: VaultFile | None = None) -> str:
    if head is not None:
        return head.name
    return f"{PurePosixPath(job.input_filename).stem}.provdokument.zip"


class ExamWorkspaceConversionProgress:
    """Progress port implementation over the job row and the versioned document store."""

    def __init__(
        self,
        *,
        jobs: ExamAnswerKeyEnrichmentJobRepositoryProtocol,
        users: UserRepositoryProtocol,
        vault_files: VaultFileRepositoryProtocol,
        store: ExamWorkspaceDocumentStore,
        codec: ExamWorkspaceContainerCodecProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._jobs = jobs
        self._users = users
        self._vault_files = vault_files
        self._store = store
        self._codec = codec
        self._uow = uow
        self._clock = clock
        self._ids = id_generator

    async def outline(self, *, worker_id: str, job_id: UUID, outline: ConversionOutline) -> None:
        async with self._uow:
            job = await self._owned_job(job_id=job_id, worker_id=worker_id)
            if job is None or job.conversion_progress is not None:
                return
            progress = ConversionProgress.from_question_ids(
                question.question_id for question in outline.questions
            )
            await self._jobs.set_conversion_progress(
                job_id=job_id, progress=progress.model_dump(mode="json")
            )

    async def batch_ready(self, *, worker_id: str, job_id: UUID, update: ConversionUpdate) -> None:
        for attempt in range(1, _SAVE_ATTEMPTS + 1):
            file_id = self._ids.new_uuid()
            actor: User | None = None
            try:
                async with self._uow:
                    job = await self._owned_job(job_id=job_id, worker_id=worker_id)
                    if job is None:
                        return
                    actor = await self._users.get_by_id(job.owner_user_id)
                    if actor is None:
                        return
                    await self._publish(
                        job=job,
                        actor=actor,
                        file_id=file_id,
                        update=update,
                        notes=None,
                    )
                return
            except DomainError as error:
                if actor is not None:
                    await self._store.discard_version_file(actor=actor, file_id=file_id)
                if error.code is not ErrorCode.CONFLICT or attempt == _SAVE_ATTEMPTS:
                    raise
            except BaseException:
                if actor is not None:
                    await self._store.discard_version_file(actor=actor, file_id=file_id)
                raise

    async def publish_final(
        self,
        *,
        worker_id: str,
        job_id: UUID,
        lineage_id: UUID,
        actor: User,
        file_id: UUID,
        update: ConversionUpdate,
        notes: tuple[str, ...],
    ) -> None:
        job = await self._owned_job(job_id=job_id, worker_id=worker_id)
        if job is None or job.workspace_lineage_id != lineage_id:
            raise DomainError(
                code=ErrorCode.CONFLICT, message="Konverteringen ägs inte längre av arbetaren."
            )
        for attempt in range(1, _SAVE_ATTEMPTS + 1):
            try:
                async with self._uow:
                    await self._publish(
                        job=job,
                        actor=actor,
                        file_id=file_id,
                        update=update,
                        notes=notes,
                    )
                return
            except DomainError as error:
                if error.code is not ErrorCode.CONFLICT or attempt == _SAVE_ATTEMPTS:
                    raise

    async def abandon(self, *, worker_id: str, job_id: UUID, reason: str) -> None:
        job = await self._owned_job(job_id=job_id, worker_id=worker_id)
        if job is None or job.conversion_progress is None:
            return
        progress = ConversionProgress.model_validate(job.conversion_progress)
        if progress.revision is None:
            return
        actor = await self._users.get_by_id(job.owner_user_id)
        if actor is None:
            return
        for attempt in range(1, _SAVE_ATTEMPTS + 1):
            file_id = self._ids.new_uuid()
            try:
                async with self._uow:
                    loaded = await self._load_head(job=job, actor=actor)
                    if loaded is None:
                        return
                    head_file, head = loaded
                    target = abandon_target(head=head.document, progress=progress, reason=reason)
                    merged = merge_conversion(head=head.document, progress=progress, target=target)
                    await self._write(
                        job=job,
                        actor=actor,
                        file_id=file_id,
                        name=_version_name(job, head_file),
                        merged=merged,
                        head_file=head_file,
                        assets_by_id=head.assets_by_id,
                        notes=head.notes,
                    )
                return
            except DomainError as error:
                await self._store.discard_version_file(actor=actor, file_id=file_id)
                if error.code is not ErrorCode.CONFLICT or attempt == _SAVE_ATTEMPTS:
                    raise

    async def _owned_job(
        self, *, job_id: UUID, worker_id: str
    ) -> ExamAnswerKeyEnrichmentJob | None:
        job = await self._jobs.get_by_id_for_update(job_id=job_id)
        if (
            job is None
            or job.status is not ExamAnswerKeyEnrichmentJobStatus.RUNNING
            or job.locked_by != worker_id
            or job.locked_until is None
            or job.locked_until <= self._clock.now()
            or job.workspace_lineage_id is None
        ):
            return None
        return job

    async def _load_head(
        self, *, job: ExamAnswerKeyEnrichmentJob, actor: User
    ) -> tuple[VaultFile, ExamWorkspaceContainerContent] | None:
        assert job.workspace_lineage_id is not None
        head = await self._vault_files.get_document_head(
            user_id=actor.id, document_lineage_id=job.workspace_lineage_id
        )
        if head is None or head.document_version is None:
            return None
        content = await self._store.load_version(actor=actor, vault_file=head)
        return head, self._codec.parse(content=content)

    async def _publish(
        self,
        *,
        job: ExamAnswerKeyEnrichmentJob,
        actor: User,
        file_id: UUID,
        update: ConversionUpdate,
        notes: tuple[str, ...] | None,
    ) -> None:
        """Merge ``update`` into the head and save it; ``notes`` is set only by the final save."""
        progress = (
            ConversionProgress.model_validate(job.conversion_progress)
            if job.conversion_progress is not None
            else ConversionProgress.from_question_ids(update.item_ids)
        )
        loaded = await self._load_head(job=job, actor=actor)
        if loaded is None:
            assert job.workspace_lineage_id is not None
            merged = first_conversion(update=update, progress=progress)
            document = merged.document.model_copy(update={"document_id": job.workspace_lineage_id})
            await self._write(
                job=job,
                actor=actor,
                file_id=file_id,
                name=_version_name(job),
                merged=ConversionMerge(document=document, progress=merged.progress, changed=True),
                head_file=None,
                assets_by_id=_referenced_payloads(document, update.assets_by_id),
                notes=notes or (),
            )
            return
        head_file, head = loaded
        merged = merge_conversion(
            head=head.document, progress=progress, target=target_from_update(update)
        )
        await self._write(
            job=job,
            actor=actor,
            file_id=file_id,
            name=_version_name(job, head_file),
            merged=merged,
            head_file=head_file,
            assets_by_id=_referenced_payloads(
                merged.document, {**head.assets_by_id, **update.assets_by_id}
            ),
            notes=head.notes if notes is None else notes,
            notes_changed=notes is not None and notes != head.notes,
        )

    async def _write(
        self,
        *,
        job: ExamAnswerKeyEnrichmentJob,
        actor: User,
        file_id: UUID,
        name: str,
        merged: ConversionMerge,
        head_file: VaultFile | None,
        assets_by_id: dict[str, bytes],
        notes: tuple[str, ...],
        notes_changed: bool = False,
    ) -> None:
        """Save the merged revision and retire the conversion revision it supersedes."""
        assert job.workspace_lineage_id is not None
        progress = merged.progress
        if merged.changed or notes_changed:
            content = self._codec.build(
                content=ExamWorkspaceContainerContent(
                    document=merged.document, assets_by_id=assets_by_id, notes=notes
                )
            )
            await self._store.save_version(
                actor=actor,
                file_id=file_id,
                name=name,
                content=content,
                lineage_id=job.workspace_lineage_id,
                version=merged.document.revision,
            )
            previous = ConversionProgress.model_validate(job.conversion_progress or {}).revision
            if head_file is not None and head_file.document_version == previous:
                await self._store.retire_version(actor=actor, retired=head_file)
            progress = progress.model_copy(update={"revision": merged.document.revision})
        await self._jobs.set_conversion_progress(
            job_id=job.id, progress=progress.model_dump(mode="json")
        )
