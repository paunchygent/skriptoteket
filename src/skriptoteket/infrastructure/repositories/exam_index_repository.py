"""Request-scoped exam index persistence; the caller's UoW owns commit."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, or_, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.curated_apps.exam_workspace.exam_index import ExamIndexEntry, SavedExam
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document_versions import (
    CURRENT_NATIVE_EXAM_DOCUMENT_VERSION,
    OLDEST_READABLE_NATIVE_EXAM_DOCUMENT_VERSION,
)
from skriptoteket.infrastructure.db.models.exam_index import ExamIndexModel
from skriptoteket.infrastructure.db.models.user_vault_file import UserVaultFileModel
from skriptoteket.protocols.exam_index import ExamIndexRepositoryProtocol


def _joined_query(
    *,
    owner_user_id: UUID,
    readable: bool | None,
) -> Select[tuple[UUID, UUID, str | None, str, datetime, UUID, int, str, int | None]]:
    """Live saved exams; `readable` keeps the readable ones, the others, or all (None)."""
    statement = (
        select(
            ExamIndexModel.owner_user_id,
            ExamIndexModel.lineage_id,
            ExamIndexModel.course_key,
            ExamIndexModel.title,
            ExamIndexModel.saved_at,
            ExamIndexModel.head_vault_file_id,
            ExamIndexModel.document_format_version,
            UserVaultFileModel.name,
            UserVaultFileModel.document_version.label("version"),
        )
        .join(UserVaultFileModel, UserVaultFileModel.id == ExamIndexModel.head_vault_file_id)
        .where(
            ExamIndexModel.owner_user_id == owner_user_id,
            UserVaultFileModel.user_id == owner_user_id,
            UserVaultFileModel.document_lineage_id == ExamIndexModel.lineage_id,
            UserVaultFileModel.export_format.is_(None),
            UserVaultFileModel.deleted_at.is_(None),
        )
        .order_by(ExamIndexModel.saved_at.desc(), ExamIndexModel.lineage_id)
    )
    if readable is True:
        return statement.where(
            ExamIndexModel.document_format_version >= OLDEST_READABLE_NATIVE_EXAM_DOCUMENT_VERSION,
            ExamIndexModel.document_format_version <= CURRENT_NATIVE_EXAM_DOCUMENT_VERSION,
        )
    if readable is False:
        return statement.where(
            or_(
                ExamIndexModel.document_format_version
                < OLDEST_READABLE_NATIVE_EXAM_DOCUMENT_VERSION,
                ExamIndexModel.document_format_version > CURRENT_NATIVE_EXAM_DOCUMENT_VERSION,
            )
        )
    return statement


class PostgreSQLExamIndexRepository(ExamIndexRepositoryProtocol):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(self, *, entry: ExamIndexEntry) -> None:
        statement = insert(ExamIndexModel).values(**entry.model_dump())
        await self._session.execute(
            statement.on_conflict_do_update(
                index_elements=["owner_user_id", "lineage_id"],
                set_={
                    key: getattr(statement.excluded, key)
                    for key in (
                        "course_key",
                        "title",
                        "saved_at",
                        "head_vault_file_id",
                        "document_format_version",
                    )
                },
            )
        )

    async def list_for_owner(self, *, owner_user_id: UUID) -> list[SavedExam]:
        rows = await self._session.execute(
            _joined_query(owner_user_id=owner_user_id, readable=True)
        )
        return [SavedExam.model_validate(row) for row in rows.mappings()]

    async def list_unreadable_for_owner(self, *, owner_user_id: UUID) -> list[SavedExam]:
        rows = await self._session.execute(
            _joined_query(owner_user_id=owner_user_id, readable=False)
        )
        return [SavedExam.model_validate(row) for row in rows.mappings()]

    async def get(self, *, owner_user_id: UUID, lineage_id: UUID) -> SavedExam | None:
        result = await self._session.execute(
            _joined_query(owner_user_id=owner_user_id, readable=None).where(
                ExamIndexModel.lineage_id == lineage_id
            )
        )
        row = result.mappings().one_or_none()
        return None if row is None else SavedExam.model_validate(row)

    async def lock_owner_titles(self, *, owner_user_id: UUID) -> None:
        await self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"),
            {"lock_key": f"exam-index-titles:{owner_user_id}"},
        )

    async def titles_like(self, *, owner_user_id: UUID, base: str) -> set[str]:
        escaped = base.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        rows = await self._session.execute(
            select(ExamIndexModel.title).where(
                ExamIndexModel.owner_user_id == owner_user_id,
                or_(
                    ExamIndexModel.title == base,
                    ExamIndexModel.title.like(f"{escaped} (%", escape="\\"),
                ),
            )
        )
        return set(rows.scalars().all())
