"""Exam workspace undo-history persistence for the user vault repository.

The history head, edit lease, steps and content-addressed assets of one exam
lineage are rows of their own tables. The vault file repository delegates its
history operations here and keeps the vault file rows and locks itself.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import asc, delete, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.application.curated_apps.exam_workspace_history import (
    ExamWorkspaceEditLease,
    ExamWorkspaceHistoryCursor,
    ExamWorkspaceHistoryStepRef,
    ExamWorkspaceHistoryStoredStep,
    dump_step_document,
    load_step_document,
)
from skriptoteket.infrastructure.db.models.user_vault_file import (
    ExamWorkspaceHistoryAssetModel,
    ExamWorkspaceHistoryModel,
    ExamWorkspaceHistoryStepModel,
)


class ExamWorkspaceHistoryPersistence:
    """Reads and writes the undo history rows of exam workspace lineages."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_history_head(
        self, *, user_id: UUID, document_lineage_id: UUID
    ) -> ExamWorkspaceHistoryCursor | None:
        result = await self._session.execute(
            select(
                ExamWorkspaceHistoryModel.cursor,
                ExamWorkspaceHistoryModel.current_step_id,
                ExamWorkspaceHistoryModel.baseline_step_id,
            ).where(
                ExamWorkspaceHistoryModel.user_id == user_id,
                ExamWorkspaceHistoryModel.lineage_id == document_lineage_id,
            )
        )
        row = result.one_or_none()
        if row is None:
            return None
        return ExamWorkspaceHistoryCursor(
            cursor=row[0], current_step_id=row[1], baseline_step_id=row[2]
        )

    async def upsert_history_head(
        self,
        *,
        user_id: UUID,
        document_lineage_id: UUID,
        head: ExamWorkspaceHistoryCursor,
    ) -> None:
        await self._session.execute(
            pg_insert(ExamWorkspaceHistoryModel)
            .values(
                user_id=user_id,
                lineage_id=document_lineage_id,
                cursor=head.cursor,
                current_step_id=head.current_step_id,
                baseline_step_id=head.baseline_step_id,
            )
            .on_conflict_do_update(
                index_elements=["user_id", "lineage_id"],
                set_={
                    "cursor": head.cursor,
                    "current_step_id": head.current_step_id,
                    "baseline_step_id": head.baseline_step_id,
                },
            )
        )

    async def get_history_lease(
        self, *, user_id: UUID, document_lineage_id: UUID
    ) -> ExamWorkspaceEditLease | None:
        result = await self._session.execute(
            select(
                ExamWorkspaceHistoryModel.lease_holder_tab_id,
                ExamWorkspaceHistoryModel.lease_renewed_at,
                ExamWorkspaceHistoryModel.lease_takeover_requested_by,
            ).where(
                ExamWorkspaceHistoryModel.user_id == user_id,
                ExamWorkspaceHistoryModel.lineage_id == document_lineage_id,
            )
        )
        row = result.one_or_none()
        if row is None:
            return None
        return ExamWorkspaceEditLease(
            holder_tab_id=row[0],
            renewed_at=row[1],
            takeover_requested_by=row[2],
        )

    async def upsert_history_lease(
        self, *, user_id: UUID, document_lineage_id: UUID, lease: ExamWorkspaceEditLease
    ) -> None:
        await self._session.execute(
            update(ExamWorkspaceHistoryModel)
            .where(
                ExamWorkspaceHistoryModel.user_id == user_id,
                ExamWorkspaceHistoryModel.lineage_id == document_lineage_id,
            )
            .values(
                lease_holder_tab_id=lease.holder_tab_id,
                lease_renewed_at=lease.renewed_at,
                lease_takeover_requested_by=lease.takeover_requested_by,
            )
        )

    async def get_history_step(
        self, *, user_id: UUID, document_lineage_id: UUID, step_id: UUID
    ) -> ExamWorkspaceHistoryStoredStep | None:
        result = await self._session.execute(
            select(ExamWorkspaceHistoryStepModel).where(
                ExamWorkspaceHistoryStepModel.user_id == user_id,
                ExamWorkspaceHistoryStepModel.lineage_id == document_lineage_id,
                ExamWorkspaceHistoryStepModel.step_id == step_id,
            )
        )
        model = result.scalar_one_or_none()
        return self._stored_step(model) if model is not None else None

    async def list_history_step_refs(
        self, *, user_id: UUID, document_lineage_id: UUID
    ) -> list[ExamWorkspaceHistoryStepRef]:
        result = await self._session.execute(
            select(
                ExamWorkspaceHistoryStepModel.step_id,
                ExamWorkspaceHistoryStepModel.position,
                ExamWorkspaceHistoryStepModel.asset_ids,
            )
            .where(
                ExamWorkspaceHistoryStepModel.user_id == user_id,
                ExamWorkspaceHistoryStepModel.lineage_id == document_lineage_id,
            )
            .order_by(asc(ExamWorkspaceHistoryStepModel.position))
        )
        return [
            ExamWorkspaceHistoryStepRef(step_id=row[0], position=row[1], asset_ids=tuple(row[2]))
            for row in result.all()
        ]

    async def list_history_steps(
        self, *, user_id: UUID, document_lineage_id: UUID
    ) -> list[ExamWorkspaceHistoryStoredStep]:
        result = await self._session.execute(
            select(ExamWorkspaceHistoryStepModel)
            .where(
                ExamWorkspaceHistoryStepModel.user_id == user_id,
                ExamWorkspaceHistoryStepModel.lineage_id == document_lineage_id,
            )
            .order_by(asc(ExamWorkspaceHistoryStepModel.position))
        )
        return [self._stored_step(model) for model in result.scalars().all()]

    @staticmethod
    def _stored_step(model: ExamWorkspaceHistoryStepModel) -> ExamWorkspaceHistoryStoredStep:
        return ExamWorkspaceHistoryStoredStep(
            step_id=model.step_id,
            position=model.position,
            document=load_step_document(model.document),
            asset_ids=tuple(model.asset_ids),
            notes=tuple(model.notes),
        )

    async def get_history_assets(
        self, *, user_id: UUID, document_lineage_id: UUID, asset_ids: tuple[str, ...]
    ) -> dict[str, bytes]:
        if not asset_ids:
            return {}
        result = await self._session.execute(
            select(
                ExamWorkspaceHistoryAssetModel.asset_id, ExamWorkspaceHistoryAssetModel.content
            ).where(
                ExamWorkspaceHistoryAssetModel.user_id == user_id,
                ExamWorkspaceHistoryAssetModel.lineage_id == document_lineage_id,
                ExamWorkspaceHistoryAssetModel.asset_id.in_(asset_ids),
            )
        )
        return {row[0]: row[1] for row in result.all()}

    async def insert_history_step(
        self,
        *,
        user_id: UUID,
        document_lineage_id: UUID,
        step: ExamWorkspaceHistoryStoredStep,
        assets_by_id: dict[str, bytes],
    ) -> None:
        self._session.add(
            ExamWorkspaceHistoryStepModel(
                user_id=user_id,
                lineage_id=document_lineage_id,
                step_id=step.step_id,
                position=step.position,
                document=dump_step_document(step.document),
                asset_ids=list(step.asset_ids),
                notes=list(step.notes),
            )
        )
        # Asset ids are content-addressed, so a stored picture never changes;
        # an autosave that references the same picture writes no picture bytes.
        if assets_by_id:
            existing = await self._session.execute(
                select(ExamWorkspaceHistoryAssetModel.asset_id).where(
                    ExamWorkspaceHistoryAssetModel.user_id == user_id,
                    ExamWorkspaceHistoryAssetModel.lineage_id == document_lineage_id,
                    ExamWorkspaceHistoryAssetModel.asset_id.in_(assets_by_id),
                )
            )
            present = set(existing.scalars().all())
            for asset_id, content in assets_by_id.items():
                if asset_id in present:
                    continue
                await self._session.execute(
                    pg_insert(ExamWorkspaceHistoryAssetModel)
                    .values(
                        user_id=user_id,
                        lineage_id=document_lineage_id,
                        asset_id=asset_id,
                        content=content,
                    )
                    .on_conflict_do_nothing(
                        index_elements=["user_id", "lineage_id", "asset_id"],
                    )
                )

    async def delete_history_steps(
        self, *, user_id: UUID, document_lineage_id: UUID, step_ids: list[UUID]
    ) -> None:
        if not step_ids:
            return
        await self._session.execute(
            delete(ExamWorkspaceHistoryStepModel).where(
                ExamWorkspaceHistoryStepModel.user_id == user_id,
                ExamWorkspaceHistoryStepModel.lineage_id == document_lineage_id,
                ExamWorkspaceHistoryStepModel.step_id.in_(step_ids),
            )
        )

    async def delete_orphan_history_assets(
        self, *, user_id: UUID, document_lineage_id: UUID, keep_asset_ids: frozenset[str]
    ) -> None:
        statement = delete(ExamWorkspaceHistoryAssetModel).where(
            ExamWorkspaceHistoryAssetModel.user_id == user_id,
            ExamWorkspaceHistoryAssetModel.lineage_id == document_lineage_id,
        )
        if keep_asset_ids:
            statement = statement.where(
                ExamWorkspaceHistoryAssetModel.asset_id.not_in(keep_asset_ids)
            )
        await self._session.execute(statement)

    async def delete_history(self, *, user_id: UUID, document_lineage_id: UUID) -> None:
        await self._session.execute(
            delete(ExamWorkspaceHistoryStepModel).where(
                ExamWorkspaceHistoryStepModel.user_id == user_id,
                ExamWorkspaceHistoryStepModel.lineage_id == document_lineage_id,
            )
        )
        await self._session.execute(
            delete(ExamWorkspaceHistoryAssetModel).where(
                ExamWorkspaceHistoryAssetModel.user_id == user_id,
                ExamWorkspaceHistoryAssetModel.lineage_id == document_lineage_id,
            )
        )
        await self._session.execute(
            delete(ExamWorkspaceHistoryModel).where(
                ExamWorkspaceHistoryModel.user_id == user_id,
                ExamWorkspaceHistoryModel.lineage_id == document_lineage_id,
            )
        )
