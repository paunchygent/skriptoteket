"""Persistence boundary for the exam-owned saved index."""

from typing import Protocol
from uuid import UUID

from skriptoteket.domain.curated_apps.exam_workspace.exam_index import ExamIndexEntry, SavedExam


class ExamIndexRepositoryProtocol(Protocol):
    async def upsert(self, *, entry: ExamIndexEntry) -> None: ...

    async def list_for_owner(self, *, owner_user_id: UUID) -> list[SavedExam]: ...

    async def list_unreadable_for_owner(self, *, owner_user_id: UUID) -> list[SavedExam]: ...

    async def get(self, *, owner_user_id: UUID, lineage_id: UUID) -> SavedExam | None: ...

    async def lock_owner_titles(self, *, owner_user_id: UUID) -> None:
        """Hold the owner's title lock until the transaction ends."""

    async def titles_like(self, *, owner_user_id: UUID, base: str) -> set[str]:
        """Return the owner's titles equal to ``base`` or starting with ``base (``."""
