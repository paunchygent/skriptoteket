"""One mutable vault file per exam, with revision-checked writes."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager
from uuid import UUID, uuid4

from skriptoteket.application.curated_apps.exam_workspace_history import (
    ExamWorkspaceHistoryCursor,
    ExamWorkspaceHistoryResponse,
    ExamWorkspaceHistoryState,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_history_rows import (
    ExamWorkspaceHistoryRowStore,
)
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.exam_workspace.exam_course_catalog import (
    load_exam_course_catalog,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_index import ExamIndexEntry
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import NativeExamDocument
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document_versions import (
    CURRENT_NATIVE_EXAM_DOCUMENT_VERSION,
)
from skriptoteket.domain.errors import DomainError, ErrorCode, validation_error
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.vault import VaultFile, VaultFileSourceKind, VaultUsage
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.exam_index import ExamIndexRepositoryProtocol
from skriptoteket.protocols.exam_workspace import ExamWorkspaceContainerCodecProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from skriptoteket.protocols.vault import (
    VaultFileRepositoryProtocol,
    VaultStorageProtocol,
    VaultUsageRepositoryProtocol,
)

EXAM_WORKSPACE_SOURCE_ARTIFACT_PREFIX = "documents.conversion_hub:exam-workspace"


def _vault_full_error() -> DomainError:
    return validation_error(
        "Mina filer är fullt; ta bort filer och försök igen.",
        details={"reason": "vault_full"},
    )


class ExamWorkspaceDocumentStore:
    """Serialize writes against the lineage lock and account for replaced bytes."""

    def __init__(
        self,
        *,
        vault_files: VaultFileRepositoryProtocol,
        vault_usage: VaultUsageRepositoryProtocol,
        vault_storage: VaultStorageProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        settings: Settings,
        index: ExamIndexRepositoryProtocol,
        codec: ExamWorkspaceContainerCodecProtocol,
    ) -> None:
        self._vault_files = vault_files
        self._vault_usage = vault_usage
        self._vault_storage = vault_storage
        self._uow = uow
        self._clock = clock
        self._settings = settings
        self._index = index
        self._codec = codec
        self._rows = ExamWorkspaceHistoryRowStore(
            vault_files=vault_files, vault_storage=vault_storage, codec=codec
        )
        self._rollback_frames: list[list[tuple[UUID, UUID, bytes | None]]] = []
        self._payload_guards: set[tuple[UUID, UUID]] = set()
        self._guard_stack = AsyncExitStack()

    @asynccontextmanager
    async def transaction(self, *, user_id: UUID, lineage_id: UUID) -> AsyncIterator[None]:
        """Keep payload exclusion through SQL commit and any filesystem compensation.

        Acquire before application row/lineage locks. Nested operations enlist both
        their journal and their guards in the outermost transaction.
        """
        outermost = not self._rollback_frames
        frame: list[tuple[UUID, UUID, bytes | None]] = []
        key = (user_id, lineage_id)
        try:
            if key not in self._payload_guards:
                await self._guard_stack.enter_async_context(
                    self._vault_files.guard_document_payload(
                        user_id=user_id, document_lineage_id=lineage_id
                    )
                )
                self._payload_guards.add(key)
            self._rollback_frames.append(frame)
            try:
                async with self._uow:
                    yield
            except BaseException:
                for owner_id, file_id, content in reversed(frame):
                    if content is None:
                        await self._vault_storage.delete_file(user_id=owner_id, file_id=file_id)
                    else:
                        await self._vault_storage.store_file(
                            user_id=owner_id, file_id=file_id, content=content
                        )
                raise
            else:
                if len(self._rollback_frames) > 1:
                    self._rollback_frames[-2].extend(frame)
            finally:
                self._rollback_frames.pop()
        finally:
            if outermost:
                await self._guard_stack.aclose()
                self._payload_guards.clear()

    async def save(
        self,
        *,
        actor: User,
        file_id: UUID,
        name: str,
        content: bytes,
        lineage_id: UUID,
        version: int,
        expected_revision: int | None = None,
        export_format: str | None = None,
        preserve_editor_position: bool = False,
    ) -> VaultFile:
        """Write the exam file; a first save also creates the baseline history step."""
        self.validate_size(content)
        document = (
            None if export_format is not None else self._codec.parse(content=content).document
        )
        if document is not None:
            if document.document_id != lineage_id or document.revision != version:
                raise validation_error("Dokumentets identitet eller version matchar inte filen.")
            if document.header.course is not None and document.header.course.key not in {
                course.key for course in load_exam_course_catalog().courses
            }:
                raise validation_error(
                    "Välj en kurs ur kurslistan.", details={"field": "course_key"}
                )
        actual_bytes = len(content)
        previous_content: bytes | None = None
        now = self._clock.now()
        async with self.transaction(user_id=actor.id, lineage_id=lineage_id):
            await self._vault_files.lock_document_lineage(
                user_id=actor.id, document_lineage_id=lineage_id
            )
            if export_format is None:
                head = await self._vault_files.get_document_head(
                    user_id=actor.id, document_lineage_id=lineage_id
                )
            else:
                files = await self._vault_files.list_exam_files(
                    user_id=actor.id, document_lineage_id=lineage_id, include_deleted=True
                )
                head = next(
                    (item for item in files if item.export_format == export_format),
                    None,
                )
            current_revision = None if head is None else head.document_version
            if export_format is None and current_revision != expected_revision:
                raise DomainError(
                    code=ErrorCode.CONFLICT,
                    message="Dokumentet har ändrats sedan det öppnades.",
                    details={
                        "expected_revision": expected_revision,
                        "current_revision": current_revision,
                    },
                )
            if head is not None:
                vault_file = await self._overwrite_head_file(
                    actor=actor,
                    lineage_id=lineage_id,
                    head=head,
                    name=head.name if export_format is None else name,
                    content=content,
                    document=document,
                    version=version,
                )
            else:
                usage = await self._vault_usage.get_for_update(user_id=actor.id, now=now)
                total = usage.bytes_total + actual_bytes
                if total > self._settings.VAULT_MAX_TOTAL_BYTES:
                    raise _vault_full_error()
                vault_file = await self._vault_files.create(
                    file=VaultFile(
                        id=file_id,
                        user_id=actor.id,
                        name=name,
                        bytes=actual_bytes,
                        source_kind=VaultFileSourceKind.APP_EXPORT,
                        source_artifact_id=f"{EXAM_WORKSPACE_SOURCE_ARTIFACT_PREFIX}:{lineage_id}"
                        + (f":{export_format}" if export_format else ""),
                        document_lineage_id=lineage_id,
                        document_version=version,
                        export_format=export_format,
                        document_saved_at=now,
                        created_at=now,
                    )
                )
                if document is not None:
                    await self._index.upsert(
                        entry=ExamIndexEntry(
                            owner_user_id=actor.id,
                            lineage_id=lineage_id,
                            course_key=None
                            if document.header.course is None
                            else document.header.course.key,
                            title=document.title,
                            saved_at=now,
                            head_vault_file_id=vault_file.id,
                            document_format_version=CURRENT_NATIVE_EXAM_DOCUMENT_VERSION,
                        )
                    )
                self._rollback_frames[-1].append((actor.id, file_id, previous_content))
                await self._vault_storage.store_file(
                    user_id=actor.id, file_id=file_id, content=content
                )
                await self._vault_usage.upsert(
                    usage=VaultUsage(user_id=actor.id, bytes_total=total, updated_at=now)
                )
            if export_format is None and head is None:
                await self._rows.init_history(actor=actor, lineage_id=lineage_id, content=content)
            elif export_format is None and not preserve_editor_position:
                raise ValueError("A save of an existing exam preserves the editor's position.")
            elif export_format is None:
                head_row = await self.ensure_history_head(actor=actor, lineage_id=lineage_id)
                await self._vault_files.upsert_history_head(
                    user_id=actor.id,
                    document_lineage_id=lineage_id,
                    head=head_row.model_copy(update={"cursor": uuid4()}),
                )
        return vault_file

    async def _overwrite_head_file(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        head: VaultFile,
        name: str,
        content: bytes,
        document: NativeExamDocument | None,
        version: int,
    ) -> VaultFile:
        """Overwrite one existing exam file row, its index entry, blob and usage.

        The caller holds ``transaction`` and the lineage lock, so the head cannot move
        under the write. Usage, quota and rollback accounting match ``save``.
        """
        now = self._clock.now()
        usage = await self._vault_usage.get_for_update(user_id=actor.id, now=now)
        counted_bytes = head.bytes if head.deleted_at is None else 0
        total = usage.bytes_total + len(content) - counted_bytes
        if total > self._settings.VAULT_MAX_TOTAL_BYTES:
            raise _vault_full_error()
        file_id = head.id
        previous_content: bytes | None = None
        if await self._vault_storage.exists_file(user_id=actor.id, file_id=file_id):
            previous_content = await self.load(actor=actor, vault_file=head)
        if head.deleted_at is not None:
            head = await self._vault_files.update(
                file=head.model_copy(update={"deleted_at": None, "trashed_with_exam": False})
            )
        vault_file = await self._vault_files.overwrite(
            file=head.model_copy(
                update={
                    "bytes": len(content),
                    "document_version": version,
                    "document_saved_at": now,
                    "name": name,
                }
            )
        )
        if document is not None:
            await self._index.upsert(
                entry=ExamIndexEntry(
                    owner_user_id=actor.id,
                    lineage_id=lineage_id,
                    course_key=None
                    if document.header.course is None
                    else document.header.course.key,
                    title=document.title,
                    saved_at=now,
                    head_vault_file_id=vault_file.id,
                    document_format_version=CURRENT_NATIVE_EXAM_DOCUMENT_VERSION,
                )
            )
        self._rollback_frames[-1].append((actor.id, file_id, previous_content))
        await self._vault_storage.store_file(user_id=actor.id, file_id=file_id, content=content)
        await self._vault_usage.upsert(
            usage=VaultUsage(user_id=actor.id, bytes_total=total, updated_at=now)
        )
        return vault_file

    async def write_step_file(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        content: bytes,
        document: NativeExamDocument,
        version: int,
    ) -> VaultFile:
        """Overwrite the exam file for one stored undo step or one position move.

        The caller holds ``transaction`` and the lineage lock and passes the head version
        plus one; the cursor stays the only guard while the server assigns the revision.
        """
        if document.document_id != lineage_id or document.revision != version:
            raise validation_error("Dokumentets identitet eller version matchar inte filen.")
        if document.header.course is not None and document.header.course.key not in {
            course.key for course in load_exam_course_catalog().courses
        }:
            raise validation_error("Välj en kurs ur kurslistan.", details={"field": "course_key"})
        head = await self._vault_files.get_document_head(
            user_id=actor.id, document_lineage_id=lineage_id
        )
        assert head is not None
        return await self._overwrite_head_file(
            actor=actor,
            lineage_id=lineage_id,
            head=head,
            name=head.name,
            content=content,
            document=document,
            version=version,
        )

    def validate_size(self, content: bytes) -> None:
        if not content or len(content) > self._settings.VAULT_MAX_FILE_BYTES:
            raise validation_error("Dokumentets storlek är inte tillåten.")

    async def ensure_history_head(
        self, *, actor: User, lineage_id: UUID
    ) -> ExamWorkspaceHistoryCursor:
        """Read the exam's history row, recreating the baseline from the file when missing."""
        return await self._rows.ensure_head(actor=actor, lineage_id=lineage_id)

    async def get_history(self, *, actor: User, lineage_id: UUID) -> ExamWorkspaceHistoryState:
        """Rebuild the retained snapshots from their step rows and the picture store."""
        return await self._rows.get_state(actor=actor, lineage_id=lineage_id)

    async def put_history(
        self, *, actor: User, lineage_id: UUID, history: ExamWorkspaceHistoryState
    ) -> None:
        """Replace every step row, used when conversion delivery rewrites all snapshots."""
        await self._rows.replace_state(actor=actor, lineage_id=lineage_id, history=history)

    async def append_history_step(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        head: ExamWorkspaceHistoryCursor,
        step_id: UUID,
        document: NativeExamDocument,
        assets_by_id: dict[str, bytes],
        notes: tuple[str, ...],
        after_step_id: UUID,
    ) -> ExamWorkspaceHistoryResponse:
        """Insert one step row and move the head row; other step rows stay untouched."""
        return await self._rows.append_step(
            actor=actor,
            lineage_id=lineage_id,
            head=head,
            step_id=step_id,
            document=document,
            assets_by_id=assets_by_id,
            notes=notes,
            after_step_id=after_step_id,
        )

    async def move_history_position(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        head: ExamWorkspaceHistoryCursor,
        step_id: UUID,
        new_cursor: UUID,
    ) -> ExamWorkspaceHistoryResponse:
        """Move the editor's position; the only write is the history head row."""
        return await self._rows.move_position(
            actor=actor,
            lineage_id=lineage_id,
            head=head,
            step_id=step_id,
            new_cursor=new_cursor,
        )

    async def get_history_step_document(
        self, *, actor: User, lineage_id: UUID, step_id: UUID
    ) -> NativeExamDocument:
        return await self._rows.step_document(actor=actor, lineage_id=lineage_id, step_id=step_id)

    async def load(self, *, actor: User, vault_file: VaultFile) -> bytes:
        return await self._vault_storage.read_file(user_id=actor.id, file_id=vault_file.id)
