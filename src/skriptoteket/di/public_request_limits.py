"""DI bindings for the database-backed public request limiter (ST-SKRIPT-41-02 G3)."""

from __future__ import annotations

from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.application.public_request_limits import AdmitPublicRequestHandler
from skriptoteket.config import Settings
from skriptoteket.infrastructure.repositories.public_request_windows import (
    PostgreSQLPublicRequestWindowRepository,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.public_request_limits import (
    AdmitPublicRequestHandlerProtocol,
    PublicRequestBucket,
    PublicRequestWindowRepositoryProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class PublicRequestLimitsProvider(Provider):
    """Provide the shared hourly window repository and its admission handler."""

    @provide(scope=Scope.REQUEST)
    def public_request_window_repository(
        self, session: AsyncSession
    ) -> PublicRequestWindowRepositoryProtocol:
        return PostgreSQLPublicRequestWindowRepository(session)

    @provide(scope=Scope.REQUEST)
    def admit_public_request_handler(
        self,
        uow: UnitOfWorkProtocol,
        windows: PublicRequestWindowRepositoryProtocol,
        clock: ClockProtocol,
        settings: Settings,
    ) -> AdmitPublicRequestHandlerProtocol:
        return AdmitPublicRequestHandler(
            uow=uow,
            windows=windows,
            clock=clock,
            limits={
                PublicRequestBucket.GUEST_IMPORT: (
                    settings.PUBLIC_GUEST_IMPORT_CALLER_PER_HOUR,
                    settings.PUBLIC_GUEST_IMPORT_POOL_PER_HOUR,
                ),
                PublicRequestBucket.GUEST_EXPORT: (
                    settings.PUBLIC_GUEST_EXPORT_CALLER_PER_HOUR,
                    settings.PUBLIC_GUEST_EXPORT_POOL_PER_HOUR,
                ),
                PublicRequestBucket.GUEST_EDIT: (
                    settings.PUBLIC_GUEST_EDIT_CALLER_PER_HOUR,
                    settings.PUBLIC_GUEST_EDIT_POOL_PER_HOUR,
                ),
            },
        )
