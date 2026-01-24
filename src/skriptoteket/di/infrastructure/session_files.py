"""Infrastructure provider: session file storage."""

from __future__ import annotations

from dishka import Provider, Scope, provide

from skriptoteket.config import Settings
from skriptoteket.infrastructure.session_files.file_ref_resolver import (
    SessionFileRefResolver,
)
from skriptoteket.infrastructure.session_files.local_session_file_storage import (
    LocalSessionFileStorage,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.file_refs import FileRefResolverProtocol
from skriptoteket.protocols.session_files import SessionFileStorageProtocol


class InfrastructureSessionFilesProvider(Provider):
    """Provides session file storage bindings."""

    @provide(scope=Scope.APP)
    def session_file_storage(
        self,
        settings: Settings,
        clock: ClockProtocol,
    ) -> SessionFileStorageProtocol:
        return LocalSessionFileStorage(
            sessions_root=settings.ARTIFACTS_ROOT,
            ttl_seconds=settings.SESSION_FILES_TTL_SECONDS,
            clock=clock,
        )

    @provide(scope=Scope.APP)
    def file_ref_resolver(
        self,
        session_files: SessionFileStorageProtocol,
    ) -> FileRefResolverProtocol:
        return SessionFileRefResolver(session_files=session_files)
