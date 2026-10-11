"""DI bindings for the item-type labeler (TASK-SKRIPT-39-05-04).

The Decisions adapter is app-scoped and stateless; the leased labeler is
request-scoped so its reservations share the request UoW.
"""

from __future__ import annotations

import httpx
from dishka import Provider, Scope, provide

from skriptoteket.application.curated_apps.item_type_labeling import LeasedItemTypeLabeler
from skriptoteket.config import Settings
from skriptoteket.infrastructure.llm.openai.decisions_item_labeler import (
    OpenAIDecisionsItemTypeLabeler,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.exam_answer_key import AnswerKeyTokenLeaseRepositoryProtocol
from skriptoteket.protocols.item_type_labeler import (
    ItemTypeLabelerProtocol,
    MeteredItemTypeLabelerProtocol,
)
from skriptoteket.protocols.sleeper import SleeperProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class ItemTypeLabelerProvider(Provider):
    """Provide the Decisions item-type labeler behind the daily token lease."""

    @provide(scope=Scope.APP)
    def decisions_item_type_labeler(
        self, client: httpx.AsyncClient, sleeper: SleeperProtocol, settings: Settings
    ) -> MeteredItemTypeLabelerProtocol:
        return OpenAIDecisionsItemTypeLabeler(
            client=client,
            base_url=settings.LLM_ANSWER_KEY_BASE_URL,
            api_key=settings.OPENAI_LLM_ANSWER_KEY_API_KEY,
            timeout_seconds=float(settings.LLM_ITEM_LABELER_TIMEOUT_SECONDS),
            sleeper=sleeper,
        )

    @provide(scope=Scope.REQUEST)
    def item_type_labeler(
        self,
        labeler: MeteredItemTypeLabelerProtocol,
        leases: AnswerKeyTokenLeaseRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
    ) -> ItemTypeLabelerProtocol:
        return LeasedItemTypeLabeler(labeler=labeler, leases=leases, uow=uow, clock=clock)
