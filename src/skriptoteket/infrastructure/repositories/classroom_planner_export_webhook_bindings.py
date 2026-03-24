"""PostgreSQL repository for shared seating-export webhook bindings.

Purpose:
    Expose the single shared Sir Convert webhook binding through a dedicated
    repository so seating export-job orchestration can coordinate subscription
    creation under a row lock instead of using job rows as ad hoc ownership.

Relationships:
    - Implements `SeatingExportWebhookBindingRepositoryProtocol`.
    - Maps `SeatingExportWebhookBindingModel` to the application-layer binding
      model.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.application.curated_apps.classroom_planner.exports.webhook_bindings import (
    SeatingExportWebhookBinding,
)
from skriptoteket.infrastructure.db.models.classroom_planner_seating_export_webhook_binding import (
    SeatingExportWebhookBindingModel,
)
from skriptoteket.protocols.classroom_planner_exports import (
    SeatingExportWebhookBindingRepositoryProtocol,
)

_SHARED_BINDING_KEY = "classroom-planner-seating-export"


class PostgreSQLSeatingExportWebhookBindingRepository(
    SeatingExportWebhookBindingRepositoryProtocol
):
    """Persist the canonical seating-export webhook binding in PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_binding(
        self,
        model: SeatingExportWebhookBindingModel,
    ) -> SeatingExportWebhookBinding:
        return SeatingExportWebhookBinding(
            binding_key=model.binding_key,
            subscription_id=model.subscription_id,
            callback_url=model.callback_url,
            secret=model.secret,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def get_shared_for_update(self) -> SeatingExportWebhookBinding:
        result = await self._session.execute(
            select(SeatingExportWebhookBindingModel)
            .where(SeatingExportWebhookBindingModel.binding_key == _SHARED_BINDING_KEY)
            .with_for_update()
        )
        model = result.scalar_one()
        return self._to_binding(model)

    async def update_shared(
        self,
        *,
        binding: SeatingExportWebhookBinding,
    ) -> SeatingExportWebhookBinding:
        model = await self._session.get(SeatingExportWebhookBindingModel, binding.binding_key)
        if model is None:
            return binding

        model.subscription_id = binding.subscription_id
        model.callback_url = binding.callback_url
        model.secret = binding.secret

        await self._session.flush()
        await self._session.refresh(model)
        return self._to_binding(model)
