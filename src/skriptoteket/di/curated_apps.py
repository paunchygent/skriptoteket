"""Curated apps provider: app-specific handlers and services."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import httpx
from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.application.curated_apps.classroom_planner import (
    AbandonDraftHandler,
    ActivateGroupingHistoryDraftHandler,
    ActivateSeatingHistoryDraftHandler,
    CompleteSeatingExportJobFromWebhookHandler,
    CreateGroupingDraftHandler,
    CreateGroupingExportJobHandler,
    CreateRoomTemplateHandler,
    CreateRosterHandler,
    CreateSeatingDraftHandler,
    CreateSeatingExportJobHandler,
    DeleteHistoricGroupingDraftHandler,
    DeleteHistoricSeatingDraftHandler,
    DeleteRoomTemplateHandler,
    DeleteRosterHandler,
    DownloadGroupingExportJobHandler,
    DownloadSeatingExportJobHandler,
    GetClassWorkspaceSummaryHandler,
    GetDraftHandler,
    GetDraftWorkspaceHandler,
    GetGroupingExportJobHandler,
    GetRecoverableGroupingExportJobForDraftHandler,
    GetRecoverableSeatingExportJobForDraftHandler,
    GetResumableDraftHandler,
    GetRoomTemplateHandler,
    GetRosterHandler,
    GetSeatingExportJobHandler,
    GroupingExportJobFinalizer,
    ListRoomTemplatesHandler,
    ListRostersHandler,
    PatchDraftHandler,
    PrepareGroupingExportHandler,
    PrepareSeatingExportHandler,
    RedoDraftHandler,
    ResolveDraftHandler,
    SeatingExportJobFinalizer,
    UndoDraftHandler,
    UpdateRoomTemplateHandler,
    UpdateRosterHandler,
)
from skriptoteket.application.curated_apps.classroom_planner.handlers.imports import (
    CreateClassListImportPreviewHandler,
)
from skriptoteket.application.curated_apps.flunk_out_frenzy import (
    GetFlunkOutFrenzyBootstrapHandler,
)
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
from skriptoteket.domain.curated_apps.classroom_planner.import_heuristics import (
    ClassListHeuristicParser,
)
from skriptoteket.infrastructure.curated_apps.apps.classroom_planner import (
    class_list_document_extractor as class_list_document_extractor_module,
)
from skriptoteket.infrastructure.curated_apps.apps.classroom_planner.grouping_xlsx_renderer import (
    GroupingXlsxRenderer,
)
from skriptoteket.infrastructure.curated_apps.apps.classroom_planner.poster_renderer import (
    BrutalistPosterRenderer,
)
from skriptoteket.infrastructure.curated_apps.apps.classroom_planner.seating_xlsx_renderer import (
    SeatingXlsxRenderer,
)
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
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.risk_templates_store import (
    InMemoryReagentPrepChefRiskTemplateStore,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_store import (
    FileSystemReagentPrepChefSdsStore,
)
from skriptoteket.infrastructure.repositories.classroom_planner import (
    PostgreSQLPlanDraftRepository,
    PostgreSQLRoomTemplateRepository,
    PostgreSQLRosterRepository,
)
from skriptoteket.infrastructure.repositories.classroom_planner_export_jobs import (
    PostgreSQLSeatingExportJobRepository,
)
from skriptoteket.infrastructure.repositories.classroom_planner_export_webhook_bindings import (
    PostgreSQLSeatingExportWebhookBindingRepository,
)
from skriptoteket.infrastructure.repositories.classroom_planner_grouping_export_jobs import (
    PostgreSQLGroupingExportJobRepository,
)
from skriptoteket.protocols.classroom_planner import (
    PlanDraftRepositoryProtocol,
    RoomTemplateRepositoryProtocol,
    RosterRepositoryProtocol,
)
from skriptoteket.protocols.classroom_planner_exports import (
    GroupingExportJobRepositoryProtocol,
    GroupingXlsxRendererProtocol,
    SeatingExportJobRepositoryProtocol,
    SeatingExportWebhookBindingRepositoryProtocol,
    SeatingPosterRendererProtocol,
    SeatingXlsxRendererProtocol,
)
from skriptoteket.protocols.classroom_planner_imports import (
    ClassListHeuristicParserProtocol,
    DocumentTextExtractorProtocol,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.flunk_out_frenzy import FlunkOutFrenzyBootstrapHandlerProtocol
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
    @provide(scope=Scope.REQUEST)
    def flunk_out_frenzy_bootstrap_handler(self) -> FlunkOutFrenzyBootstrapHandlerProtocol:
        return GetFlunkOutFrenzyBootstrapHandler()

    @provide(scope=Scope.APP)
    def sir_convert_a_lot_client_settings_v2(
        self, settings: Settings
    ) -> SirConvertClientSettingsV2:
        return SirConvertClientSettingsV2(
            base_url=settings.SIR_CONVERT_A_LOT_V2_BASE_URL,
            api_key=settings.SIR_CONVERT_A_LOT_V2_API_KEY,
            timeout_seconds=settings.SIR_CONVERT_A_LOT_V2_TIMEOUT_SECONDS,
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
    def reagent_prep_chef_sds_store(
        self,
        settings: Settings,
        pdf: ReagentPrepChefPdfRendererProtocol,
    ) -> ReagentPrepChefSdsStoreProtocol:
        return FileSystemReagentPrepChefSdsStore(
            index_path=Path("data/reagent_prep_chef/sds/index.json"),
            markdown_dir=Path("data/reagent_prep_chef/sds/markdown"),
            pdf_cache_dir=settings.REAGENT_PREP_CHEF_SDS_PDF_CACHE_DIR,
            pdf_renderer=pdf,
        )

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
        sds_store: ReagentPrepChefSdsStoreProtocol,
        sessions: ToolSessionRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> ReagentPrepChefRiskAssessmentHandlerProtocol:
        return ReagentPrepChefRiskAssessmentHandler(
            prep=prep,
            hazards=hazards,
            risk_templates=risk_templates,
            sds_store=sds_store,
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

    @provide(scope=Scope.REQUEST)
    def list_rosters_handler(self, rosters: RosterRepositoryProtocol) -> ListRostersHandler:
        return ListRostersHandler(rosters=rosters)

    @provide(scope=Scope.REQUEST)
    def get_roster_handler(self, rosters: RosterRepositoryProtocol) -> GetRosterHandler:
        return GetRosterHandler(rosters=rosters)

    @provide(scope=Scope.REQUEST)
    def create_roster_handler(
        self,
        uow: UnitOfWorkProtocol,
        rosters: RosterRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> CreateRosterHandler:
        return CreateRosterHandler(uow=uow, rosters=rosters, clock=clock, id_generator=id_generator)

    @provide(scope=Scope.REQUEST)
    def update_roster_handler(
        self,
        uow: UnitOfWorkProtocol,
        rosters: RosterRepositoryProtocol,
        drafts: PlanDraftRepositoryProtocol,
        clock: ClockProtocol,
    ) -> UpdateRosterHandler:
        return UpdateRosterHandler(uow=uow, rosters=rosters, drafts=drafts, clock=clock)

    @provide(scope=Scope.REQUEST)
    def delete_roster_handler(
        self,
        uow: UnitOfWorkProtocol,
        rosters: RosterRepositoryProtocol,
        drafts: PlanDraftRepositoryProtocol,
    ) -> DeleteRosterHandler:
        return DeleteRosterHandler(uow=uow, rosters=rosters, drafts=drafts)

    @provide(scope=Scope.REQUEST)
    def list_room_templates_handler(
        self, templates: RoomTemplateRepositoryProtocol
    ) -> ListRoomTemplatesHandler:
        return ListRoomTemplatesHandler(templates=templates)

    @provide(scope=Scope.REQUEST)
    def get_room_template_handler(
        self, templates: RoomTemplateRepositoryProtocol
    ) -> GetRoomTemplateHandler:
        return GetRoomTemplateHandler(templates=templates)

    @provide(scope=Scope.REQUEST)
    def create_room_template_handler(
        self,
        uow: UnitOfWorkProtocol,
        templates: RoomTemplateRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> CreateRoomTemplateHandler:
        return CreateRoomTemplateHandler(
            uow=uow, templates=templates, clock=clock, id_generator=id_generator
        )

    @provide(scope=Scope.REQUEST)
    def update_room_template_handler(
        self,
        uow: UnitOfWorkProtocol,
        templates: RoomTemplateRepositoryProtocol,
        clock: ClockProtocol,
    ) -> UpdateRoomTemplateHandler:
        return UpdateRoomTemplateHandler(uow=uow, templates=templates, clock=clock)

    @provide(scope=Scope.REQUEST)
    def delete_room_template_handler(
        self,
        uow: UnitOfWorkProtocol,
        templates: RoomTemplateRepositoryProtocol,
        drafts: PlanDraftRepositoryProtocol,
    ) -> DeleteRoomTemplateHandler:
        return DeleteRoomTemplateHandler(uow=uow, templates=templates, drafts=drafts)

    @provide(scope=Scope.REQUEST)
    def get_draft_handler(self, drafts: PlanDraftRepositoryProtocol) -> GetDraftHandler:
        return GetDraftHandler(drafts=drafts)

    @provide(scope=Scope.REQUEST)
    def get_class_workspace_summary_handler(
        self,
        rosters: RosterRepositoryProtocol,
        drafts: PlanDraftRepositoryProtocol,
    ) -> GetClassWorkspaceSummaryHandler:
        return GetClassWorkspaceSummaryHandler(rosters=rosters, drafts=drafts)

    @provide(scope=Scope.REQUEST)
    def resolve_draft_handler(
        self,
        uow: UnitOfWorkProtocol,
        rosters: RosterRepositoryProtocol,
        templates: RoomTemplateRepositoryProtocol,
        drafts: PlanDraftRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> ResolveDraftHandler:
        return ResolveDraftHandler(
            uow=uow,
            rosters=rosters,
            templates=templates,
            drafts=drafts,
            clock=clock,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def create_grouping_draft_handler(
        self,
        uow: UnitOfWorkProtocol,
        rosters: RosterRepositoryProtocol,
        templates: RoomTemplateRepositoryProtocol,
        drafts: PlanDraftRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> CreateGroupingDraftHandler:
        return CreateGroupingDraftHandler(
            uow=uow,
            rosters=rosters,
            templates=templates,
            drafts=drafts,
            clock=clock,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def activate_grouping_history_draft_handler(
        self,
        uow: UnitOfWorkProtocol,
        drafts: PlanDraftRepositoryProtocol,
        clock: ClockProtocol,
    ) -> ActivateGroupingHistoryDraftHandler:
        return ActivateGroupingHistoryDraftHandler(uow=uow, drafts=drafts, clock=clock)

    @provide(scope=Scope.REQUEST)
    def delete_historic_grouping_draft_handler(
        self,
        uow: UnitOfWorkProtocol,
        drafts: PlanDraftRepositoryProtocol,
    ) -> DeleteHistoricGroupingDraftHandler:
        return DeleteHistoricGroupingDraftHandler(uow=uow, drafts=drafts)

    @provide(scope=Scope.REQUEST)
    def create_seating_draft_handler(
        self,
        uow: UnitOfWorkProtocol,
        rosters: RosterRepositoryProtocol,
        templates: RoomTemplateRepositoryProtocol,
        drafts: PlanDraftRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> CreateSeatingDraftHandler:
        return CreateSeatingDraftHandler(
            uow=uow,
            rosters=rosters,
            templates=templates,
            drafts=drafts,
            clock=clock,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def prepare_seating_export_handler(
        self,
        drafts: PlanDraftRepositoryProtocol,
        rosters: RosterRepositoryProtocol,
        templates: RoomTemplateRepositoryProtocol,
    ) -> PrepareSeatingExportHandler:
        return PrepareSeatingExportHandler(
            drafts=drafts,
            rosters=rosters,
            templates=templates,
        )

    @provide(scope=Scope.REQUEST)
    def prepare_grouping_export_handler(
        self,
        drafts: PlanDraftRepositoryProtocol,
        rosters: RosterRepositoryProtocol,
        templates: RoomTemplateRepositoryProtocol,
    ) -> PrepareGroupingExportHandler:
        return PrepareGroupingExportHandler(
            drafts=drafts,
            rosters=rosters,
            templates=templates,
        )

    @provide(scope=Scope.REQUEST)
    def seating_export_job_handler(
        self,
        prepare: PrepareSeatingExportHandler,
        jobs: SeatingExportJobRepositoryProtocol,
        webhook_bindings: SeatingExportWebhookBindingRepositoryProtocol,
        poster_renderer: SeatingPosterRendererProtocol,
        xlsx_renderer: SeatingXlsxRendererProtocol,
        client: SirConvertALotClientV2Protocol,
        finalizer: SeatingExportJobFinalizer,
        vault_files: VaultFileRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
        settings: Settings,
    ) -> CreateSeatingExportJobHandler:
        return CreateSeatingExportJobHandler(
            prepare=prepare,
            jobs=jobs,
            webhook_bindings=webhook_bindings,
            poster_renderer=poster_renderer,
            xlsx_renderer=xlsx_renderer,
            client=client,
            finalizer=finalizer,
            vault_files=vault_files,
            uow=uow,
            clock=clock,
            id_generator=id_generator,
            settings=settings,
        )

    @provide(scope=Scope.REQUEST)
    def grouping_export_job_handler(
        self,
        prepare: PrepareGroupingExportHandler,
        jobs: GroupingExportJobRepositoryProtocol,
        xlsx_renderer: GroupingXlsxRendererProtocol,
        finalizer: GroupingExportJobFinalizer,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> CreateGroupingExportJobHandler:
        return CreateGroupingExportJobHandler(
            prepare=prepare,
            jobs=jobs,
            xlsx_renderer=xlsx_renderer,
            finalizer=finalizer,
            uow=uow,
            clock=clock,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def seating_export_job_finalizer(
        self,
        jobs: SeatingExportJobRepositoryProtocol,
        client: SirConvertALotClientV2Protocol,
        vault_files: VaultFileRepositoryProtocol,
        vault_usage: VaultUsageRepositoryProtocol,
        vault_storage: VaultStorageProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
        settings: Settings,
    ) -> SeatingExportJobFinalizer:
        return SeatingExportJobFinalizer(
            jobs=jobs,
            client=client,
            vault_files=vault_files,
            vault_usage=vault_usage,
            vault_storage=vault_storage,
            uow=uow,
            clock=clock,
            id_generator=id_generator,
            settings=settings,
        )

    @provide(scope=Scope.REQUEST)
    def grouping_export_job_finalizer(
        self,
        jobs: GroupingExportJobRepositoryProtocol,
        vault_files: VaultFileRepositoryProtocol,
        vault_usage: VaultUsageRepositoryProtocol,
        vault_storage: VaultStorageProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
        settings: Settings,
    ) -> GroupingExportJobFinalizer:
        return GroupingExportJobFinalizer(
            jobs=jobs,
            vault_files=vault_files,
            vault_usage=vault_usage,
            vault_storage=vault_storage,
            uow=uow,
            clock=clock,
            id_generator=id_generator,
            settings=settings,
        )

    @provide(scope=Scope.REQUEST)
    def get_seating_export_job_handler(
        self,
        jobs: SeatingExportJobRepositoryProtocol,
        vault_files: VaultFileRepositoryProtocol,
        client: SirConvertALotClientV2Protocol,
        finalizer: SeatingExportJobFinalizer,
        uow: UnitOfWorkProtocol,
    ) -> GetSeatingExportJobHandler:
        return GetSeatingExportJobHandler(
            jobs=jobs,
            vault_files=vault_files,
            client=client,
            finalizer=finalizer,
            uow=uow,
        )

    @provide(scope=Scope.REQUEST)
    def get_grouping_export_job_handler(
        self,
        jobs: GroupingExportJobRepositoryProtocol,
        vault_files: VaultFileRepositoryProtocol,
        uow: UnitOfWorkProtocol,
    ) -> GetGroupingExportJobHandler:
        return GetGroupingExportJobHandler(
            jobs=jobs,
            vault_files=vault_files,
            uow=uow,
        )

    @provide(scope=Scope.REQUEST)
    def get_recoverable_seating_export_job_for_draft_handler(
        self,
        jobs: SeatingExportJobRepositoryProtocol,
        vault_files: VaultFileRepositoryProtocol,
        client: SirConvertALotClientV2Protocol,
        finalizer: SeatingExportJobFinalizer,
        uow: UnitOfWorkProtocol,
    ) -> GetRecoverableSeatingExportJobForDraftHandler:
        return GetRecoverableSeatingExportJobForDraftHandler(
            jobs=jobs,
            vault_files=vault_files,
            client=client,
            finalizer=finalizer,
            uow=uow,
        )

    @provide(scope=Scope.REQUEST)
    def get_recoverable_grouping_export_job_for_draft_handler(
        self,
        jobs: GroupingExportJobRepositoryProtocol,
        vault_files: VaultFileRepositoryProtocol,
        uow: UnitOfWorkProtocol,
    ) -> GetRecoverableGroupingExportJobForDraftHandler:
        return GetRecoverableGroupingExportJobForDraftHandler(
            jobs=jobs,
            vault_files=vault_files,
            uow=uow,
        )

    @provide(scope=Scope.REQUEST)
    def complete_seating_export_job_from_webhook_handler(
        self,
        jobs: SeatingExportJobRepositoryProtocol,
        finalizer: SeatingExportJobFinalizer,
        uow: UnitOfWorkProtocol,
    ) -> CompleteSeatingExportJobFromWebhookHandler:
        return CompleteSeatingExportJobFromWebhookHandler(
            jobs=jobs,
            finalizer=finalizer,
            uow=uow,
        )

    @provide(scope=Scope.REQUEST)
    def download_seating_export_job_handler(
        self,
        jobs: SeatingExportJobRepositoryProtocol,
        vault_files: VaultFileRepositoryProtocol,
        vault_storage: VaultStorageProtocol,
        uow: UnitOfWorkProtocol,
    ) -> DownloadSeatingExportJobHandler:
        return DownloadSeatingExportJobHandler(
            jobs=jobs,
            vault_files=vault_files,
            vault_storage=vault_storage,
            uow=uow,
        )

    @provide(scope=Scope.REQUEST)
    def download_grouping_export_job_handler(
        self,
        jobs: GroupingExportJobRepositoryProtocol,
        vault_files: VaultFileRepositoryProtocol,
        vault_storage: VaultStorageProtocol,
        uow: UnitOfWorkProtocol,
    ) -> DownloadGroupingExportJobHandler:
        return DownloadGroupingExportJobHandler(
            jobs=jobs,
            vault_files=vault_files,
            vault_storage=vault_storage,
            uow=uow,
        )

    @provide(scope=Scope.REQUEST)
    def activate_seating_history_draft_handler(
        self,
        uow: UnitOfWorkProtocol,
        drafts: PlanDraftRepositoryProtocol,
        clock: ClockProtocol,
    ) -> ActivateSeatingHistoryDraftHandler:
        return ActivateSeatingHistoryDraftHandler(uow=uow, drafts=drafts, clock=clock)

    @provide(scope=Scope.REQUEST)
    def delete_historic_seating_draft_handler(
        self,
        uow: UnitOfWorkProtocol,
        drafts: PlanDraftRepositoryProtocol,
    ) -> DeleteHistoricSeatingDraftHandler:
        return DeleteHistoricSeatingDraftHandler(uow=uow, drafts=drafts)

    @provide(scope=Scope.REQUEST)
    def undo_draft_handler(
        self,
        uow: UnitOfWorkProtocol,
        drafts: PlanDraftRepositoryProtocol,
    ) -> UndoDraftHandler:
        return UndoDraftHandler(uow=uow, drafts=drafts)

    @provide(scope=Scope.REQUEST)
    def redo_draft_handler(
        self,
        uow: UnitOfWorkProtocol,
        drafts: PlanDraftRepositoryProtocol,
    ) -> RedoDraftHandler:
        return RedoDraftHandler(uow=uow, drafts=drafts)

    @provide(scope=Scope.REQUEST)
    def get_resumable_draft_handler(
        self, drafts: PlanDraftRepositoryProtocol
    ) -> GetResumableDraftHandler:
        return GetResumableDraftHandler(drafts=drafts)

    @provide(scope=Scope.REQUEST)
    def abandon_draft_handler(
        self,
        uow: UnitOfWorkProtocol,
        drafts: PlanDraftRepositoryProtocol,
        clock: ClockProtocol,
    ) -> AbandonDraftHandler:
        return AbandonDraftHandler(uow=uow, drafts=drafts, clock=clock)

    @provide(scope=Scope.REQUEST)
    def get_draft_workspace_handler(
        self,
        drafts: PlanDraftRepositoryProtocol,
        rosters: RosterRepositoryProtocol,
        templates: RoomTemplateRepositoryProtocol,
    ) -> GetDraftWorkspaceHandler:
        return GetDraftWorkspaceHandler(drafts=drafts, rosters=rosters, templates=templates)

    @provide(scope=Scope.REQUEST)
    def patch_draft_handler(
        self,
        uow: UnitOfWorkProtocol,
        drafts: PlanDraftRepositoryProtocol,
        rosters: RosterRepositoryProtocol,
        templates: RoomTemplateRepositoryProtocol,
        clock: ClockProtocol,
    ) -> PatchDraftHandler:
        return PatchDraftHandler(
            uow=uow,
            drafts=drafts,
            rosters=rosters,
            templates=templates,
            clock=clock,
        )

    @provide(scope=Scope.REQUEST)
    def plan_draft_repository(self, session: AsyncSession) -> PlanDraftRepositoryProtocol:
        return PostgreSQLPlanDraftRepository(session=session)

    @provide(scope=Scope.REQUEST)
    def roster_repository(self, session: AsyncSession) -> RosterRepositoryProtocol:
        return PostgreSQLRosterRepository(session=session)

    @provide(scope=Scope.REQUEST)
    def room_template_repository(self, session: AsyncSession) -> RoomTemplateRepositoryProtocol:
        return PostgreSQLRoomTemplateRepository(session=session)

    @provide(scope=Scope.REQUEST)
    def seating_export_job_repository(
        self, session: AsyncSession
    ) -> SeatingExportJobRepositoryProtocol:
        return PostgreSQLSeatingExportJobRepository(session=session)

    @provide(scope=Scope.REQUEST)
    def grouping_export_job_repository(
        self, session: AsyncSession
    ) -> GroupingExportJobRepositoryProtocol:
        return PostgreSQLGroupingExportJobRepository(session=session)

    @provide(scope=Scope.REQUEST)
    def seating_export_webhook_binding_repository(
        self,
        session: AsyncSession,
    ) -> SeatingExportWebhookBindingRepositoryProtocol:
        return PostgreSQLSeatingExportWebhookBindingRepository(session=session)

    @provide(scope=Scope.APP)
    def seating_poster_renderer(self) -> SeatingPosterRendererProtocol:
        return BrutalistPosterRenderer()

    @provide(scope=Scope.APP)
    def seating_xlsx_renderer(self) -> SeatingXlsxRendererProtocol:
        return SeatingXlsxRenderer()

    @provide(scope=Scope.APP)
    def grouping_xlsx_renderer(self) -> GroupingXlsxRendererProtocol:
        return GroupingXlsxRenderer()

    @provide(scope=Scope.APP)
    def class_list_document_extractor(
        self, settings: Settings, client: SirConvertALotClientV2Protocol
    ) -> DocumentTextExtractorProtocol:
        return class_list_document_extractor_module.ClassListDocumentExtractor(
            settings=settings,
            sir_convert=client,
        )

    @provide(scope=Scope.APP)
    def class_list_heuristic_parser(self) -> ClassListHeuristicParserProtocol:
        return ClassListHeuristicParser()

    @provide(scope=Scope.REQUEST)
    def create_class_list_import_preview_handler(
        self,
        extractor: DocumentTextExtractorProtocol,
        parser: ClassListHeuristicParserProtocol,
    ) -> CreateClassListImportPreviewHandler:
        return CreateClassListImportPreviewHandler(extractor=extractor, parser=parser)
