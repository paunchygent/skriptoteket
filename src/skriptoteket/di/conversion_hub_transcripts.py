"""DI bindings for Conversion Hub transcripts and transcript formatter exports.

Saved transcript and speaker-overlay handlers, transcript formatter producer,
formatter export and artifact repositories, and their handlers.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.application.curated_apps.handlers import (
    conversion_hub_transcript_artifact_actions as transcript_artifact_action_handlers,
)
from skriptoteket.application.curated_apps.handlers import (
    conversion_hub_transcript_formatter_exports as transcript_export_handlers,
)
from skriptoteket.application.curated_apps.handlers.conversion_hub_transcript_saves import (
    GetConversionHubTranscriptHandler,
    ListConversionHubTranscriptSpeakerOverlaysHandler,
    SaveConversionHubTranscriptHandler,
    UpdateConversionHubTranscriptSpeakerOverlaysHandler,
)
from skriptoteket.config import Settings
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub import (
    sir_convert_transcript_formatter_producer as transcript_formatter_producer,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.sir_convert_client_v2 import (
    SirConvertClientSettingsV2,
    build_sir_convert_async_http_client,
)
from skriptoteket.infrastructure.repositories import (
    conversion_hub_transcript_formatter_export_states as export_state_repositories,
)
from skriptoteket.infrastructure.repositories.conversion_hub_jobs import (
    PostgreSQLConversionHubJobRepository,
)
from skriptoteket.infrastructure.repositories.conversion_hub_saved_transcripts import (
    PostgreSQLConversionHubSavedTranscriptRepository,
    PostgreSQLConversionHubTranscriptSpeakerOverlayRepository,
)
from skriptoteket.infrastructure.repositories.conversion_hub_transcript_formatter_artifacts import (
    PostgreSQLConversionHubTranscriptFormatterArtifactRepository,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.conversion_hub import (
    ConversionHubJobRepositoryProtocol,
    ConversionHubSavedTranscriptRepositoryProtocol,
    ConversionHubTranscriptFormatterArtifactRepositoryProtocol,
    ConversionHubTranscriptFormatterExportArtifactRepositoryProtocol,
    ConversionHubTranscriptFormatterExportJobRepositoryProtocol,
    ConversionHubTranscriptFormatterExportStateRepositoryProtocol,
    ConversionHubTranscriptFormatterProducerProtocol,
    ConversionHubTranscriptSpeakerOverlayRepositoryProtocol,
)
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from skriptoteket.protocols.vault import (
    VaultFileRepositoryProtocol,
    VaultStorageProtocol,
    VaultUsageRepositoryProtocol,
)

DownloadTranscriptArtifactHandler = (
    transcript_artifact_action_handlers.DownloadConversionHubTranscriptFormatterArtifactHandler
)
SaveTranscriptArtifactHandler = (
    transcript_artifact_action_handlers.SaveConversionHubTranscriptFormatterArtifactHandler
)


class ConversionHubTranscriptProvider(Provider):
    """Provide Conversion Hub transcript and transcript formatter bindings."""

    @provide(scope=Scope.APP)
    async def transcript_formatter_producer(
        self,
        settings: SirConvertClientSettingsV2,
    ) -> AsyncIterator[ConversionHubTranscriptFormatterProducerProtocol]:
        http_client = build_sir_convert_async_http_client(settings=settings)
        try:
            yield transcript_formatter_producer.SirConvertTranscriptFormatterProducerV2(
                settings=settings,
                client=http_client,
            )
        finally:
            await http_client.aclose()

    @provide(scope=Scope.REQUEST)
    def conversion_hub_transcript_formatter_export_job_repository(
        self,
        session: AsyncSession,
    ) -> ConversionHubTranscriptFormatterExportJobRepositoryProtocol:
        return PostgreSQLConversionHubJobRepository(session=session)

    @provide(scope=Scope.REQUEST)
    def conversion_hub_saved_transcript_repository(
        self,
        session: AsyncSession,
    ) -> ConversionHubSavedTranscriptRepositoryProtocol:
        return PostgreSQLConversionHubSavedTranscriptRepository(session=session)

    @provide(scope=Scope.REQUEST)
    def conversion_hub_transcript_speaker_overlay_repository(
        self,
        session: AsyncSession,
    ) -> ConversionHubTranscriptSpeakerOverlayRepositoryProtocol:
        return PostgreSQLConversionHubTranscriptSpeakerOverlayRepository(session=session)

    @provide(scope=Scope.REQUEST)
    def conversion_hub_transcript_formatter_artifact_repository(
        self,
        session: AsyncSession,
    ) -> ConversionHubTranscriptFormatterArtifactRepositoryProtocol:
        return PostgreSQLConversionHubTranscriptFormatterArtifactRepository(session=session)

    @provide(scope=Scope.REQUEST)
    def conversion_hub_transcript_formatter_export_artifact_repository(
        self,
        session: AsyncSession,
    ) -> ConversionHubTranscriptFormatterExportArtifactRepositoryProtocol:
        return PostgreSQLConversionHubTranscriptFormatterArtifactRepository(session=session)

    @provide(scope=Scope.REQUEST)
    def conversion_hub_transcript_formatter_export_state_repository(
        self,
        session: AsyncSession,
    ) -> ConversionHubTranscriptFormatterExportStateRepositoryProtocol:
        return export_state_repositories.PostgreSQLTranscriptFormatterExportStateRepository(
            session=session
        )

    @provide(scope=Scope.REQUEST)
    def save_conversion_hub_transcript_handler(
        self,
        jobs: ConversionHubJobRepositoryProtocol,
        transcripts: ConversionHubSavedTranscriptRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> SaveConversionHubTranscriptHandler:
        return SaveConversionHubTranscriptHandler(
            jobs=jobs,
            transcripts=transcripts,
            uow=uow,
            clock=clock,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def get_conversion_hub_transcript_handler(
        self,
        transcripts: ConversionHubSavedTranscriptRepositoryProtocol,
        uow: UnitOfWorkProtocol,
    ) -> GetConversionHubTranscriptHandler:
        return GetConversionHubTranscriptHandler(
            transcripts=transcripts,
            uow=uow,
        )

    @provide(scope=Scope.REQUEST)
    def list_conversion_hub_transcript_speaker_overlays_handler(
        self,
        transcripts: ConversionHubSavedTranscriptRepositoryProtocol,
        speaker_overlays: ConversionHubTranscriptSpeakerOverlayRepositoryProtocol,
        uow: UnitOfWorkProtocol,
    ) -> ListConversionHubTranscriptSpeakerOverlaysHandler:
        return ListConversionHubTranscriptSpeakerOverlaysHandler(
            transcripts=transcripts,
            speaker_overlays=speaker_overlays,
            uow=uow,
        )

    @provide(scope=Scope.REQUEST)
    def update_conversion_hub_transcript_speaker_overlays_handler(
        self,
        transcripts: ConversionHubSavedTranscriptRepositoryProtocol,
        speaker_overlays: ConversionHubTranscriptSpeakerOverlayRepositoryProtocol,
        formatter_artifacts: ConversionHubTranscriptFormatterArtifactRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> UpdateConversionHubTranscriptSpeakerOverlaysHandler:
        return UpdateConversionHubTranscriptSpeakerOverlaysHandler(
            transcripts=transcripts,
            speaker_overlays=speaker_overlays,
            formatter_artifacts=formatter_artifacts,
            uow=uow,
            clock=clock,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def request_conversion_hub_transcript_formatter_export_handler(
        self,
        jobs: ConversionHubJobRepositoryProtocol,
        transcripts: ConversionHubSavedTranscriptRepositoryProtocol,
        speaker_overlays: ConversionHubTranscriptSpeakerOverlayRepositoryProtocol,
        artifacts: ConversionHubTranscriptFormatterArtifactRepositoryProtocol,
        export_states: ConversionHubTranscriptFormatterExportStateRepositoryProtocol,
        producer: ConversionHubTranscriptFormatterProducerProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> transcript_export_handlers.RequestConversionHubTranscriptFormatterExportHandler:
        return transcript_export_handlers.RequestConversionHubTranscriptFormatterExportHandler(
            jobs=jobs,
            transcripts=transcripts,
            speaker_overlays=speaker_overlays,
            artifacts=artifacts,
            export_states=export_states,
            producer=producer,
            uow=uow,
            clock=clock,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def get_conversion_hub_transcript_formatter_export_handler(
        self,
        jobs: ConversionHubTranscriptFormatterExportJobRepositoryProtocol,
        transcripts: ConversionHubSavedTranscriptRepositoryProtocol,
        artifacts: ConversionHubTranscriptFormatterExportArtifactRepositoryProtocol,
        export_states: ConversionHubTranscriptFormatterExportStateRepositoryProtocol,
        uow: UnitOfWorkProtocol,
    ) -> transcript_export_handlers.GetConversionHubTranscriptFormatterExportHandler:
        return transcript_export_handlers.GetConversionHubTranscriptFormatterExportHandler(
            jobs=jobs,
            transcripts=transcripts,
            artifacts=artifacts,
            export_states=export_states,
            uow=uow,
        )

    @provide(scope=Scope.REQUEST)
    def download_conversion_hub_transcript_formatter_artifact_handler(
        self,
        jobs: ConversionHubJobRepositoryProtocol,
        transcripts: ConversionHubSavedTranscriptRepositoryProtocol,
        artifacts: ConversionHubTranscriptFormatterArtifactRepositoryProtocol,
        uow: UnitOfWorkProtocol,
    ) -> DownloadTranscriptArtifactHandler:
        return DownloadTranscriptArtifactHandler(
            jobs=jobs,
            transcripts=transcripts,
            artifacts=artifacts,
            uow=uow,
        )

    @provide(scope=Scope.REQUEST)
    def save_conversion_hub_transcript_formatter_artifact_handler(
        self,
        jobs: ConversionHubJobRepositoryProtocol,
        transcripts: ConversionHubSavedTranscriptRepositoryProtocol,
        artifacts: ConversionHubTranscriptFormatterArtifactRepositoryProtocol,
        vault_files: VaultFileRepositoryProtocol,
        vault_usage: VaultUsageRepositoryProtocol,
        vault_storage: VaultStorageProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
        settings: Settings,
    ) -> SaveTranscriptArtifactHandler:
        return SaveTranscriptArtifactHandler(
            jobs=jobs,
            transcripts=transcripts,
            artifacts=artifacts,
            vault_files=vault_files,
            vault_usage=vault_usage,
            vault_storage=vault_storage,
            uow=uow,
            clock=clock,
            id_generator=id_generator,
            settings=settings,
        )
