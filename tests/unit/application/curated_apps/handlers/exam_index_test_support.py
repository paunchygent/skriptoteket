"""In-memory index port joined against the shared vault fake for handler tests."""

from uuid import UUID

from skriptoteket.domain.curated_apps.exam_workspace.exam_index import ExamIndexEntry, SavedExam
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document_versions import (
    is_readable_native_exam_document_version,
)
from tests.unit.application.curated_apps.handlers.vault_file_repository_test_support import (
    InMemoryVaultFileRepository,
)


class InMemoryExamIndexRepository:
    def __init__(self, vault_files: InMemoryVaultFileRepository) -> None:
        self.entries: dict[tuple[UUID, UUID], ExamIndexEntry] = {}
        self.vault_files = vault_files
        self.locks: list[UUID] = []

    async def upsert(self, *, entry: ExamIndexEntry) -> None:
        self.entries[entry.owner_user_id, entry.lineage_id] = entry

    async def list_for_owner(self, *, owner_user_id: UUID) -> list[SavedExam]:
        return [
            exam
            for exam in self._joined(owner_user_id=owner_user_id)
            if is_readable_native_exam_document_version(exam.document_format_version)
        ]

    async def list_unreadable_for_owner(self, *, owner_user_id: UUID) -> list[SavedExam]:
        return [
            exam
            for exam in self._joined(owner_user_id=owner_user_id)
            if not is_readable_native_exam_document_version(exam.document_format_version)
        ]

    def _joined(self, *, owner_user_id: UUID) -> list[SavedExam]:
        exams = []
        for entry in self.entries.values():
            file = self.vault_files.files.get(entry.head_vault_file_id)
            if entry.owner_user_id != owner_user_id or file is None or file.deleted_at is not None:
                continue
            assert file.document_version is not None
            exams.append(
                SavedExam(**entry.model_dump(), name=file.name, version=file.document_version)
            )
        return exams

    async def get(self, *, owner_user_id: UUID, lineage_id: UUID) -> SavedExam | None:
        return next(
            (
                exam
                for exam in self._joined(owner_user_id=owner_user_id)
                if exam.lineage_id == lineage_id
            ),
            None,
        )

    async def lock_owner_titles(self, *, owner_user_id: UUID) -> None:
        self.locks.append(owner_user_id)

    async def titles_like(self, *, owner_user_id: UUID, base: str) -> set[str]:
        return {
            entry.title
            for entry in self.entries.values()
            if entry.owner_user_id == owner_user_id
            and (entry.title == base or entry.title.startswith(f"{base} ("))
        }
