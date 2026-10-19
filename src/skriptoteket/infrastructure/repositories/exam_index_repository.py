"""Request-scoped exam index persistence; the caller's UoW owns commit."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, or_, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.curated_apps.exam_workspace.exam_index import ExamIndexEntry, SavedExam
from skriptoteket.infrastructure.db.models.exam_index import ExamIndexModel
from skriptoteket.infrastructure.db.models.user_vault_file import UserVaultFileModel
from skriptoteket.protocols.exam_index import ExamIndexRepositoryProtocol


def _joined_query(
    *,
    owner_user_id: UUID,
) -> Select[tuple[UUID, UUID, str | None, str, datetime, UUID, str, int | None]]:
    return (
        select(
            ExamIndexModel.owner_user_id,
            ExamIndexModel.lineage_id,
            ExamIndexModel.course_key,
            ExamIndexModel.title,
            ExamIndexModel.saved_at,
            ExamIndexModel.head_vault_file_id,
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
                    for key in ("course_key", "title", "saved_at", "head_vault_file_id")
                },
            )
        )

    async def list_for_owner(self, *, owner_user_id: UUID) -> list[SavedExam]:
        rows = await self._session.execute(_joined_query(owner_user_id=owner_user_id))
        return [SavedExam.model_validate(row) for row in rows.mappings()]

    async def get(self, *, owner_user_id: UUID, lineage_id: UUID) -> SavedExam | None:
        result = await self._session.execute(
            _joined_query(owner_user_id=owner_user_id).where(
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
