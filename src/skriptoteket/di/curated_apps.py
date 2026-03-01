"""Curated apps provider: app-specific handlers and services."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import httpx
from dishka import Provider, Scope, provide

from skriptoteket.application.curated_apps.handlers.reagent_prep_chef_defaults import (
    ReagentPrepChefGetDefaultsHandler,
    ReagentPrepChefUpdateDefaultsHandler,
)
from skriptoteket.application.curated_apps.handlers.reagent_prep_chef_export_pdf import (
    ReagentPrepChefExportPdfHandler,
)
from skriptoteket.application.curated_apps.handlers.reagent_prep_chef_export_risk_pdf import (
    ReagentPrepChefExportRiskPdfHandler,
)
from skriptoteket.application.curated_apps.handlers.reagent_prep_chef_list_chemicals import (
    ReagentPrepChefChemicalsHandler,
)
from skriptoteket.application.curated_apps.handlers.reagent_prep_chef_load_defaults import (
    ReagentPrepChefLoadDefaultsHandler,
)
from skriptoteket.application.curated_apps.handlers.reagent_prep_chef_prep import (
    ReagentPrepChefPrepHandler,
)
from skriptoteket.application.curated_apps.handlers.reagent_prep_chef_risk_assessment import (
    ReagentPrepChefRiskAssessmentHandler,
)
from skriptoteket.application.curated_apps.handlers.reagent_prep_chef_save_defaults import (
    ReagentPrepChefSaveDefaultsHandler,
)
from skriptoteket.application.curated_apps.handlers.reagent_prep_chef_save_pdf import (
    ReagentPrepChefSavePdfHandler,
)
from skriptoteket.application.curated_apps.handlers.reagent_prep_chef_save_risk_pdf import (
    ReagentPrepChefSaveRiskPdfHandler,
)
from skriptoteket.config import Settings
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.sir_convert_client_v2 import (
    SirConvertALotClientV2,
    SirConvertClientSettingsV2,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef import (
    hazards_store as reagent_prep_chef_hazards_store,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef import (
    risk_templates_store as reagent_prep_chef_risk_templates_store,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.hazards_store import (
    InMemoryReagentPrepChefHazardStore,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.pdf_renderer import (
    WeasyPrintPdfRenderer,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.pubchem_client import (
    PubChemClient,
    PubChemClientSettings,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.risk_templates_store import (
    InMemoryReagentPrepChefRiskTemplateStore,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_curated_meta_store import (
    CuratedSdsMetaStore,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_fetcher import (
    PubChemSdsFetcher,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_fetcher_settings import (
    SdsFetcherSettings,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_index_store import (
    FileSystemReagentPrepChefSdsIndexStore,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_pdf_providers import (
    CuratedSdsLinkoutStore,
    SdsPdfProviderRegistry,
    build_sds_pdf_provider_registry,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_store import (
    CachedReagentPrepChefSdsStore,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.reagent_prep_chef import (
    ReagentPrepChefChemicalsHandlerProtocol,
    ReagentPrepChefExportPdfHandlerProtocol,
    ReagentPrepChefExportRiskPdfHandlerProtocol,
    ReagentPrepChefGetDefaultsHandlerProtocol,
    ReagentPrepChefHazardStoreProtocol,
    ReagentPrepChefLoadDefaultsHandlerProtocol,
    ReagentPrepChefPdfRendererProtocol,
    ReagentPrepChefPrepHandlerProtocol,
    ReagentPrepChefRiskAssessmentHandlerProtocol,
    ReagentPrepChefRiskTemplateStoreProtocol,
    ReagentPrepChefSaveDefaultsHandlerProtocol,
    ReagentPrepChefSavePdfHandlerProtocol,
    ReagentPrepChefSaveRiskPdfHandlerProtocol,
    ReagentPrepChefSdsFetcherProtocol,
    ReagentPrepChefSdsIndexStoreProtocol,
    ReagentPrepChefSdsStoreProtocol,
    ReagentPrepChefUpdateDefaultsHandlerProtocol,
)
from skriptoteket.protocols.runner import ArtifactManagerProtocol
from skriptoteket.protocols.scripting import ToolRunRepositoryProtocol
from skriptoteket.protocols.sir_convert_a_lot_v2 import SirConvertALotClientV2Protocol
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from skriptoteket.protocols.vault import (
    VaultFileRepositoryProtocol,
    VaultStorageProtocol,
    VaultUsageRepositoryProtocol,
)


class CuratedAppsProvider(Provider):
    @provide(scope=Scope.APP)
    def sir_convert_a_lot_client_settings_v2(
        self, settings: Settings
    ) -> SirConvertClientSettingsV2:
        return SirConvertClientSettingsV2(
            base_url=settings.SIR_CONVERT_A_LOT_V2_BASE_URL,
            api_key=settings.SIR_CONVERT_A_LOT_V2_API_KEY,
            timeout_seconds=settings.SIR_CONVERT_A_LOT_V2_TIMEOUT_SECONDS,
        )

    @provide(scope=Scope.APP)
    async def sir_convert_a_lot_client_v2(
        self, settings: SirConvertClientSettingsV2
    ) -> AsyncIterator[SirConvertALotClientV2Protocol]:
        # Do not expose a bare `httpx.AsyncClient` in DI here: the app has other
        # async clients (for example OpenAI) and collisions would break relative
        # URL requests to Sir Convert-a-Lot v2.
        http_client = httpx.AsyncClient(
            base_url=settings.base_url,
            timeout=settings.timeout_seconds,
        )
        try:
            yield SirConvertALotClientV2(settings=settings, client=http_client)
        finally:
            await http_client.aclose()

    @provide(scope=Scope.APP)
    def reagent_prep_chef_hazards(self) -> ReagentPrepChefHazardStoreProtocol:
        hazards_path = Path(reagent_prep_chef_hazards_store.__file__).with_name("hazards.json")
        return InMemoryReagentPrepChefHazardStore(hazards_path=hazards_path)

    @provide(scope=Scope.APP)
    def reagent_prep_chef_pdf_renderer(self) -> ReagentPrepChefPdfRendererProtocol:
        return WeasyPrintPdfRenderer()

    @provide(scope=Scope.APP)
    def reagent_prep_chef_risk_templates(self) -> ReagentPrepChefRiskTemplateStoreProtocol:
        templates_path = Path(reagent_prep_chef_risk_templates_store.__file__).with_name(
            "risk_templates.json"
        )
        return InMemoryReagentPrepChefRiskTemplateStore(templates_path=templates_path)

    @provide(scope=Scope.APP)
    async def reagent_prep_chef_pubchem_client(
        self, settings: Settings
    ) -> AsyncIterator[PubChemClient]:
        client = PubChemClient(
            settings=PubChemClientSettings(
                base_url=settings.PUBCHEM_BASE_URL,
                timeout_seconds=settings.SDS_FETCH_TIMEOUT_SECONDS,
                user_agent=settings.SDS_FETCH_USER_AGENT,
                listkey_max_wait_seconds=settings.SDS_FETCH_LISTKEY_MAX_SECONDS,
                listkey_poll_interval_seconds=settings.SDS_FETCH_LISTKEY_POLL_SECONDS,
                resolve_retry_attempts=settings.SDS_FETCH_RETRY_ATTEMPTS,
                resolve_retry_backoff_seconds=settings.SDS_FETCH_RETRY_BACKOFF_SECONDS,
                resolve_retry_backoff_max_seconds=settings.SDS_FETCH_RETRY_BACKOFF_MAX_SECONDS,
                rate_limit_per_second=settings.PUBCHEM_RATE_LIMIT_PER_SECOND,
                max_in_flight=settings.PUBCHEM_MAX_IN_FLIGHT,
                throttle_yellow_delay_seconds=settings.PUBCHEM_THROTTLE_YELLOW_DELAY_SECONDS,
                throttle_red_delay_seconds=settings.PUBCHEM_THROTTLE_RED_DELAY_SECONDS,
            )
        )
        try:
            yield client
        finally:
            await client.close()

    @provide(scope=Scope.APP)
    def reagent_prep_chef_sds_pdf_registry(self, settings: Settings) -> SdsPdfProviderRegistry:
        curated_store = None
        if settings.SDS_CURATED_LINKOUTS_PATH is not None:
            curated_store = CuratedSdsLinkoutStore(path=settings.SDS_CURATED_LINKOUTS_PATH)
        return build_sds_pdf_provider_registry(curated_store=curated_store)

    @provide(scope=Scope.APP)
    def reagent_prep_chef_sds_fetcher(
        self,
        settings: Settings,
        pubchem: PubChemClient,
        sds_pdf_registry: SdsPdfProviderRegistry,
    ) -> ReagentPrepChefSdsFetcherProtocol:
        curated_meta_store = None
        if settings.SDS_CURATED_META_PATH is not None:
            curated_meta_store = CuratedSdsMetaStore(path=settings.SDS_CURATED_META_PATH)
        fetcher_settings = SdsFetcherSettings(
            timeout_seconds=settings.SDS_FETCH_TIMEOUT_SECONDS,
            user_agent=settings.SDS_FETCH_USER_AGENT,
            retry_attempts=settings.SDS_FETCH_RETRY_ATTEMPTS,
            retry_backoff_seconds=settings.SDS_FETCH_RETRY_BACKOFF_SECONDS,
            retry_backoff_max_seconds=settings.SDS_FETCH_RETRY_BACKOFF_MAX_SECONDS,
            require_pubchem_cid=True,
            cid_candidate_limit=settings.SDS_FETCH_CID_CANDIDATE_LIMIT,
            autocomplete_limit=settings.SDS_FETCH_AUTOCOMPLETE_LIMIT,
        )
        return PubChemSdsFetcher(
            pubchem=pubchem,
            settings=fetcher_settings,
            pdf_provider_registry=sds_pdf_registry,
            curated_meta_store=curated_meta_store,
        )

    @provide(scope=Scope.APP)
    def reagent_prep_chef_sds_index_store(
        self,
        settings: Settings,
        fetcher: ReagentPrepChefSdsFetcherProtocol,
    ) -> ReagentPrepChefSdsIndexStoreProtocol:
        cache_root = settings.SDS_CACHE_ROOT or (settings.ARTIFACTS_ROOT / "sds-cache")
        return FileSystemReagentPrepChefSdsIndexStore(cache_root=cache_root, fetcher=fetcher)

    @provide(scope=Scope.APP)
    def reagent_prep_chef_sds_store(
        self,
        index: ReagentPrepChefSdsIndexStoreProtocol,
    ) -> ReagentPrepChefSdsStoreProtocol:
        return CachedReagentPrepChefSdsStore(index=index)

    @provide(scope=Scope.REQUEST)
    def reagent_prep_chef_prep_handler(
        self,
        hazards: ReagentPrepChefHazardStoreProtocol,
        clock: ClockProtocol,
        settings: Settings,
    ) -> ReagentPrepChefPrepHandlerProtocol:
        return ReagentPrepChefPrepHandler(hazards=hazards, clock=clock, settings=settings)

    @provide(scope=Scope.REQUEST)
    def reagent_prep_chef_export_pdf_handler(
        self,
        prep: ReagentPrepChefPrepHandlerProtocol,
        pdf: ReagentPrepChefPdfRendererProtocol,
        uow: UnitOfWorkProtocol,
        runs: ToolRunRepositoryProtocol,
        artifacts: ArtifactManagerProtocol,
        curated_apps: CuratedAppRegistryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> ReagentPrepChefExportPdfHandlerProtocol:
        return ReagentPrepChefExportPdfHandler(
            prep=prep,
            pdf=pdf,
            uow=uow,
            runs=runs,
            artifacts=artifacts,
            curated_apps=curated_apps,
            clock=clock,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def reagent_prep_chef_risk_assessment_handler(
        self,
        prep: ReagentPrepChefPrepHandlerProtocol,
        hazards: ReagentPrepChefHazardStoreProtocol,
        risk_templates: ReagentPrepChefRiskTemplateStoreProtocol,
        sds_index: ReagentPrepChefSdsIndexStoreProtocol,
        sessions: ToolSessionRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> ReagentPrepChefRiskAssessmentHandlerProtocol:
        return ReagentPrepChefRiskAssessmentHandler(
            prep=prep,
            hazards=hazards,
            risk_templates=risk_templates,
            sds_index=sds_index,
            sessions=sessions,
            uow=uow,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def reagent_prep_chef_export_risk_pdf_handler(
        self,
        risk: ReagentPrepChefRiskAssessmentHandlerProtocol,
        pdf: ReagentPrepChefPdfRendererProtocol,
        uow: UnitOfWorkProtocol,
        runs: ToolRunRepositoryProtocol,
        artifacts: ArtifactManagerProtocol,
        curated_apps: CuratedAppRegistryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> ReagentPrepChefExportRiskPdfHandlerProtocol:
        return ReagentPrepChefExportRiskPdfHandler(
            risk=risk,
            pdf=pdf,
            uow=uow,
            runs=runs,
            artifacts=artifacts,
            curated_apps=curated_apps,
            clock=clock,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def reagent_prep_chef_save_risk_pdf_handler(
        self,
        export_pdf: ReagentPrepChefExportRiskPdfHandlerProtocol,
        uow: UnitOfWorkProtocol,
        vault_files: VaultFileRepositoryProtocol,
        vault_usage: VaultUsageRepositoryProtocol,
        vault_storage: VaultStorageProtocol,
        settings: Settings,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> ReagentPrepChefSaveRiskPdfHandlerProtocol:
        return ReagentPrepChefSaveRiskPdfHandler(
            export_pdf=export_pdf,
            uow=uow,
            vault_files=vault_files,
            vault_usage=vault_usage,
            vault_storage=vault_storage,
            settings=settings,
            clock=clock,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def reagent_prep_chef_save_pdf_handler(
        self,
        export_pdf: ReagentPrepChefExportPdfHandlerProtocol,
        uow: UnitOfWorkProtocol,
        vault_files: VaultFileRepositoryProtocol,
        vault_usage: VaultUsageRepositoryProtocol,
        vault_storage: VaultStorageProtocol,
        settings: Settings,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> ReagentPrepChefSavePdfHandlerProtocol:
        return ReagentPrepChefSavePdfHandler(
            export_pdf=export_pdf,
            uow=uow,
            vault_files=vault_files,
            vault_usage=vault_usage,
            vault_storage=vault_storage,
            settings=settings,
            clock=clock,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def reagent_prep_chef_save_defaults_handler(
        self,
        uow: UnitOfWorkProtocol,
        vault_files: VaultFileRepositoryProtocol,
        vault_usage: VaultUsageRepositoryProtocol,
        vault_storage: VaultStorageProtocol,
        settings: Settings,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> ReagentPrepChefSaveDefaultsHandlerProtocol:
        return ReagentPrepChefSaveDefaultsHandler(
            uow=uow,
            vault_files=vault_files,
            vault_usage=vault_usage,
            vault_storage=vault_storage,
            settings=settings,
            clock=clock,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def reagent_prep_chef_chemicals_handler(
        self,
        hazards: ReagentPrepChefHazardStoreProtocol,
    ) -> ReagentPrepChefChemicalsHandlerProtocol:
        return ReagentPrepChefChemicalsHandler(hazards=hazards)

    @provide(scope=Scope.REQUEST)
    def reagent_prep_chef_get_defaults_handler(
        self,
        uow: UnitOfWorkProtocol,
        sessions: ToolSessionRepositoryProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> ReagentPrepChefGetDefaultsHandlerProtocol:
        return ReagentPrepChefGetDefaultsHandler(
            uow=uow,
            sessions=sessions,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def reagent_prep_chef_update_defaults_handler(
        self,
        uow: UnitOfWorkProtocol,
        sessions: ToolSessionRepositoryProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> ReagentPrepChefUpdateDefaultsHandlerProtocol:
        return ReagentPrepChefUpdateDefaultsHandler(
            uow=uow,
            sessions=sessions,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def reagent_prep_chef_load_defaults_handler(
        self,
        uow: UnitOfWorkProtocol,
        sessions: ToolSessionRepositoryProtocol,
        id_generator: IdGeneratorProtocol,
        vault_files: VaultFileRepositoryProtocol,
        vault_storage: VaultStorageProtocol,
    ) -> ReagentPrepChefLoadDefaultsHandlerProtocol:
        return ReagentPrepChefLoadDefaultsHandler(
            uow=uow,
            sessions=sessions,
            id_generator=id_generator,
            vault_files=vault_files,
            vault_storage=vault_storage,
        )
