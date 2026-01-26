"""Infrastructure provider: session file storage."""

from __future__ import annotations

from dishka import Provider, Scope, provide

from skriptoteket.config import Settings
from skriptoteket.infrastructure.file_refs.composite_resolver import CompositeFileRefResolver
from skriptoteket.infrastructure.session_files.file_ref_resolver import SessionFileRefResolver
from skriptoteket.infrastructure.session_files.local_session_file_storage import (
    LocalSessionFileStorage,
)
from skriptoteket.infrastructure.vault.file_ref_resolver import VaultFileRefResolver
from skriptoteket.infrastructure.vault.local_vault_storage import LocalVaultStorage
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.file_refs import FileRefResolverProtocol
from skriptoteket.protocols.session_files import SessionFileStorageProtocol
from skriptoteket.protocols.vault import VaultFileRepositoryProtocol, VaultStorageProtocol


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
    def vault_storage(self, settings: Settings) -> VaultStorageProtocol:
        return LocalVaultStorage(vault_root=settings.VAULT_ROOT)

    @provide(scope=Scope.REQUEST)
    def file_ref_resolver(
        self,
        session_files: SessionFileStorageProtocol,
        vault_files: VaultFileRepositoryProtocol,
        vault_storage: VaultStorageProtocol,
    ) -> FileRefResolverProtocol:
        session_resolver = SessionFileRefResolver(session_files=session_files)
        vault_resolver = VaultFileRefResolver(
            vault_files=vault_files,
            vault_storage=vault_storage,
        )
        return CompositeFileRefResolver(
            session_resolver=session_resolver,
            vault_resolver=vault_resolver,
        )
