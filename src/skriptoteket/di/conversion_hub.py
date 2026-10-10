"""DI bindings for Conversion Hub jobs and the Sir Convert-a-Lot client.

Sir Convert-a-Lot v2 client settings and client, job repository, and the job
create, read, download, and register handlers.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.application.curated_apps.handlers.conversion_hub_jobs import (
    CreateConversionHubJobsHandler,
    DownloadConversionHubArtifactHandler,
    GetConversionHubJobHandler,
    RegisterTranscriptConversionHubJobHandler,
)
from skriptoteket.config import Settings
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.sir_convert_client_v2 import (
    SirConvertALotClientV2,
    SirConvertClientSettingsV2,
    build_sir_convert_async_http_client,
)
from skriptoteket.infrastructure.repositories.conversion_hub_jobs import (
    PostgreSQLConversionHubJobRepository,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.conversion_hub import ConversionHubJobRepositoryProtocol
from skriptoteket.protocols.exam_conversion import ExamConversionArtifactStoreProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.sir_convert_a_lot_v2 import SirConvertALotClientV2Protocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class ConversionHubProvider(Provider):
    """Provide Conversion Hub job bindings and the Sir Convert-a-Lot client."""

    @provide(scope=Scope.APP)
    def sir_convert_a_lot_client_settings_v2(
        self, settings: Settings
    ) -> SirConvertClientSettingsV2:
        return SirConvertClientSettingsV2(
            base_url=settings.SIR_CONVERT_A_LOT_V2_BASE_URL,
            api_key=settings.SIR_CONVERT_A_LOT_V2_API_KEY,
            timeout_seconds=settings.SIR_CONVERT_A_LOT_V2_TIMEOUT_SECONDS,
            unix_socket_path=settings.SIR_CONVERT_A_LOT_V2_UNIX_SOCKET_PATH or None,
            class_list_import_pdf_backend_strategy=(
                settings.SIR_CONVERT_A_LOT_V2_CLASS_LIST_IMPORT_PDF_BACKEND_STRATEGY
            ),
            class_list_import_acceleration_policy=(
                settings.SIR_CONVERT_A_LOT_V2_CLASS_LIST_IMPORT_ACCELERATION_POLICY
            ),
        )

    @provide(scope=Scope.APP)
    async def sir_convert_a_lot_client_v2(
        self, settings: SirConvertClientSettingsV2
    ) -> AsyncIterator[SirConvertALotClientV2Protocol]:
        # Do not expose a bare `httpx.AsyncClient` in DI here: the app has other
        # async clients (for example OpenAI) and collisions would break relative
        # URL requests to Sir Convert-a-Lot v2.
        http_client = build_sir_convert_async_http_client(settings=settings)
        try:
            yield SirConvertALotClientV2(settings=settings, client=http_client)
        finally:
            await http_client.aclose()

    @provide(scope=Scope.REQUEST)
    def conversion_hub_job_repository(
        self, session: AsyncSession
    ) -> ConversionHubJobRepositoryProtocol:
        return PostgreSQLConversionHubJobRepository(session=session)

    @provide(scope=Scope.REQUEST)
    def create_conversion_hub_jobs_handler(
        self,
        jobs: ConversionHubJobRepositoryProtocol,
        client: SirConvertALotClientV2Protocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> CreateConversionHubJobsHandler:
        return CreateConversionHubJobsHandler(
            jobs=jobs,
            client=client,
            uow=uow,
            clock=clock,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def get_conversion_hub_job_handler(
        self,
        jobs: ConversionHubJobRepositoryProtocol,
        client: SirConvertALotClientV2Protocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
    ) -> GetConversionHubJobHandler:
        return GetConversionHubJobHandler(
            jobs=jobs,
            client=client,
            uow=uow,
            clock=clock,
        )

    @provide(scope=Scope.REQUEST)
    def register_transcript_conversion_hub_job_handler(
        self,
        jobs: ConversionHubJobRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> RegisterTranscriptConversionHubJobHandler:
        return RegisterTranscriptConversionHubJobHandler(
            jobs=jobs,
            uow=uow,
            clock=clock,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def download_conversion_hub_artifact_handler(
        self,
        jobs: ConversionHubJobRepositoryProtocol,
        client: SirConvertALotClientV2Protocol,
        exam_artifacts: ExamConversionArtifactStoreProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
    ) -> DownloadConversionHubArtifactHandler:
        return DownloadConversionHubArtifactHandler(
            jobs=jobs,
            client=client,
            exam_artifacts=exam_artifacts,
            uow=uow,
            clock=clock,
        )
