"""Curated apps provider: app-specific handlers and services."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import httpx
from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.application.curated_apps.classroom_planner import (
    AbandonDraftHandler,
    CreateRoomTemplateHandler,
    CreateRosterHandler,
    DeleteRoomTemplateHandler,
    DeleteRosterHandler,
    GetDraftHandler,
    GetDraftWorkspaceHandler,
    GetResumableDraftHandler,
    GetRoomTemplateHandler,
    GetRosterHandler,
    ListRoomTemplatesHandler,
    ListRostersHandler,
    PatchDraftHandler,
    ResolveDraftHandler,
    UpdateRoomTemplateHandler,
    UpdateRosterHandler,
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
from skriptoteket.protocols.classroom_planner import (
    PlanDraftRepositoryProtocol,
    RoomTemplateRepositoryProtocol,
    RosterRepositoryProtocol,
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
        clock: ClockProtocol,
    ) -> UpdateRosterHandler:
        return UpdateRosterHandler(uow=uow, rosters=rosters, clock=clock)

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
