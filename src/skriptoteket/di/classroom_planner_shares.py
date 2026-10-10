"""DI bindings for classroom planner shares and guest upgrade.

Share artifact handlers, lifecycle service, public guest share handlers,
share renderers, and the guest-upgrade handlers with their repositories.
"""

from __future__ import annotations

from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.application.curated_apps.classroom_planner import (
    BackfillClassroomPlannerSharePreviewsHandler,
    ClassroomPlannerGuestUpgradeHandler,
    ClassroomPlannerShareLifecycleService,
    CreateAuthenticatedGroupingShareHandler,
    CreateAuthenticatedSeatingShareHandler,
    CreateClassroomPlannerShareArtifactHandler,
    CreatePublicGuestGroupingShareHandler,
    CreatePublicGuestSeatingShareHandler,
    GetClassroomPlannerGuestUpgradeConsumptionHandler,
    GetClassroomPlannerShareArtifactByTokenHandler,
    GetClassroomPlannerSharePreviewAssetHandler,
    ListClassroomPlannerShareArtifactsHandler,
    PrepareGroupingExportHandler,
    PrepareSeatingExportHandler,
    PublicGuestSharePolicy,
    PurgeExpiredPublicGuestShareArtifactsHandler,
    RevokeClassroomPlannerShareArtifactHandler,
    RevokePublicGuestShareHandler,
)
from skriptoteket.application.curated_apps.classroom_planner.handlers.checkpoint_recorders import (
    GroupingCheckpointRecorder,
    SeatingCheckpointRecorder,
)
from skriptoteket.config import Settings
from skriptoteket.infrastructure.curated_apps.apps.classroom_planner.share_pdf_renderer import (
    ExportBackedClassroomPlannerSharePdfRenderer,
)
from skriptoteket.infrastructure.curated_apps.apps.classroom_planner.share_preview_renderer import (
    ClassroomPlannerSharePreviewRendererSettings,
    PlaywrightClassroomPlannerSharePreviewRenderer,
)
from skriptoteket.infrastructure.curated_apps.apps.classroom_planner.share_renderer import (
    SEATING_SHARE_RENDERER_VERSION,
    StaticClassroomPlannerShareRenderer,
)
from skriptoteket.infrastructure.repositories.classroom_planner_guest_upgrade import (
    PostgreSQLClassroomPlannerGuestUpgradeRepository,
)
from skriptoteket.infrastructure.repositories.classroom_planner_share_artifacts import (
    PostgreSQLClassroomPlannerShareArtifactRepository,
)
from skriptoteket.protocols.classroom_planner import (
    GroupingExportCheckpointRepositoryProtocol,
    PlanDraftRepositoryProtocol,
    RoomTemplateRepositoryProtocol,
    RosterRepositoryProtocol,
    RosterSmartRuleRepositoryProtocol,
    SeatingExportCheckpointRepositoryProtocol,
)
from skriptoteket.protocols.classroom_planner_exports import (
    GroupingExportJobRepositoryProtocol,
    GroupingPdfRendererProtocol,
    SeatingExportJobRepositoryProtocol,
    SeatingPdfRendererProtocol,
    SeatingPosterRendererProtocol,
)
from skriptoteket.protocols.classroom_planner_guest_upgrade import (
    ClassroomPlannerGuestUpgradeRepositoryProtocol,
)
from skriptoteket.protocols.classroom_planner_shares import (
    ClassroomPlannerShareArtifactRepositoryProtocol,
    ClassroomPlannerSharePdfRendererProtocol,
    ClassroomPlannerSharePreviewRendererProtocol,
    ClassroomPlannerShareRendererProtocol,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.token_generator import TokenGeneratorProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class ClassroomPlannerShareProvider(Provider):
    """Provide classroom planner share and guest-upgrade bindings."""

    @provide(scope=Scope.REQUEST)
    def create_classroom_planner_share_artifact_handler(
        self,
        shares: ClassroomPlannerShareArtifactRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
        token_generator: TokenGeneratorProtocol,
        preview_renderer: ClassroomPlannerSharePreviewRendererProtocol,
    ) -> CreateClassroomPlannerShareArtifactHandler:
        return CreateClassroomPlannerShareArtifactHandler(
            shares=shares,
            uow=uow,
            clock=clock,
            id_generator=id_generator,
            token_generator=token_generator,
            preview_renderer=preview_renderer,
        )

    @provide(scope=Scope.REQUEST)
    def list_classroom_planner_share_artifacts_handler(
        self,
        shares: ClassroomPlannerShareArtifactRepositoryProtocol,
        uow: UnitOfWorkProtocol,
    ) -> ListClassroomPlannerShareArtifactsHandler:
        return ListClassroomPlannerShareArtifactsHandler(shares=shares, uow=uow)

    @provide(scope=Scope.REQUEST)
    def get_classroom_planner_share_artifact_by_token_handler(
        self,
        shares: ClassroomPlannerShareArtifactRepositoryProtocol,
        uow: UnitOfWorkProtocol,
    ) -> GetClassroomPlannerShareArtifactByTokenHandler:
        return GetClassroomPlannerShareArtifactByTokenHandler(shares=shares, uow=uow)

    @provide(scope=Scope.REQUEST)
    def get_classroom_planner_share_preview_asset_handler(
        self,
        shares: ClassroomPlannerShareArtifactRepositoryProtocol,
        uow: UnitOfWorkProtocol,
    ) -> GetClassroomPlannerSharePreviewAssetHandler:
        return GetClassroomPlannerSharePreviewAssetHandler(shares=shares, uow=uow)

    @provide(scope=Scope.REQUEST)
    def backfill_classroom_planner_share_previews_handler(
        self,
        shares: ClassroomPlannerShareArtifactRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        create_artifact: CreateClassroomPlannerShareArtifactHandler,
        renderer: ClassroomPlannerShareRendererProtocol,
    ) -> BackfillClassroomPlannerSharePreviewsHandler:
        return BackfillClassroomPlannerSharePreviewsHandler(
            shares=shares,
            uow=uow,
            clock=clock,
            create_artifact=create_artifact,
            renderer=renderer,
            current_seating_renderer_version=SEATING_SHARE_RENDERER_VERSION,
        )

    @provide(scope=Scope.REQUEST)
    def classroom_planner_share_lifecycle_service(
        self,
        shares: ClassroomPlannerShareArtifactRepositoryProtocol,
        clock: ClockProtocol,
    ) -> ClassroomPlannerShareLifecycleService:
        return ClassroomPlannerShareLifecycleService(shares=shares, clock=clock)

    @provide(scope=Scope.REQUEST)
    def revoke_classroom_planner_share_artifact_handler(
        self,
        shares: ClassroomPlannerShareArtifactRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
    ) -> RevokeClassroomPlannerShareArtifactHandler:
        return RevokeClassroomPlannerShareArtifactHandler(
            shares=shares,
            uow=uow,
            clock=clock,
        )

    @provide(scope=Scope.REQUEST)
    def create_authenticated_grouping_share_handler(
        self,
        prepare_grouping: PrepareGroupingExportHandler,
        create_artifact: CreateClassroomPlannerShareArtifactHandler,
        checkpoint_recorder: GroupingCheckpointRecorder,
        id_generator: IdGeneratorProtocol,
        renderer: ClassroomPlannerShareRendererProtocol,
    ) -> CreateAuthenticatedGroupingShareHandler:
        return CreateAuthenticatedGroupingShareHandler(
            prepare_grouping=prepare_grouping,
            create_artifact=create_artifact,
            checkpoint_recorder=checkpoint_recorder,
            id_generator=id_generator,
            renderer=renderer,
        )

    @provide(scope=Scope.REQUEST)
    def create_authenticated_seating_share_handler(
        self,
        prepare_seating: PrepareSeatingExportHandler,
        create_artifact: CreateClassroomPlannerShareArtifactHandler,
        checkpoint_recorder: SeatingCheckpointRecorder,
        id_generator: IdGeneratorProtocol,
        renderer: ClassroomPlannerShareRendererProtocol,
    ) -> CreateAuthenticatedSeatingShareHandler:
        return CreateAuthenticatedSeatingShareHandler(
            prepare_seating=prepare_seating,
            create_artifact=create_artifact,
            checkpoint_recorder=checkpoint_recorder,
            id_generator=id_generator,
            renderer=renderer,
        )

    @provide(scope=Scope.REQUEST)
    def public_guest_share_policy(self, settings: Settings) -> PublicGuestSharePolicy:
        return PublicGuestSharePolicy(
            ttl_days=settings.PUBLIC_HELPER_SHARE_TTL_DAYS,
            max_rendered_bytes=settings.PUBLIC_HELPER_SHARE_MAX_RENDERED_BYTES,
            max_active_per_snapshot=settings.PUBLIC_HELPER_SHARE_MAX_ACTIVE_PER_SNAPSHOT,
        )

    @provide(scope=Scope.REQUEST)
    def create_public_guest_grouping_share_handler(
        self,
        prepare_grouping: PrepareGroupingExportHandler,
        create_artifact: CreateClassroomPlannerShareArtifactHandler,
        renderer: ClassroomPlannerShareRendererProtocol,
        shares: ClassroomPlannerShareArtifactRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        policy: PublicGuestSharePolicy,
    ) -> CreatePublicGuestGroupingShareHandler:
        return CreatePublicGuestGroupingShareHandler(
            prepare_grouping=prepare_grouping,
            create_artifact=create_artifact,
            renderer=renderer,
            shares=shares,
            uow=uow,
            clock=clock,
            policy=policy,
        )

    @provide(scope=Scope.REQUEST)
    def create_public_guest_seating_share_handler(
        self,
        prepare_seating: PrepareSeatingExportHandler,
        create_artifact: CreateClassroomPlannerShareArtifactHandler,
        renderer: ClassroomPlannerShareRendererProtocol,
        shares: ClassroomPlannerShareArtifactRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        policy: PublicGuestSharePolicy,
    ) -> CreatePublicGuestSeatingShareHandler:
        return CreatePublicGuestSeatingShareHandler(
            prepare_seating=prepare_seating,
            create_artifact=create_artifact,
            renderer=renderer,
            shares=shares,
            uow=uow,
            clock=clock,
            policy=policy,
        )

    @provide(scope=Scope.REQUEST)
    def purge_expired_public_guest_share_artifacts_handler(
        self,
        shares: ClassroomPlannerShareArtifactRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
    ) -> PurgeExpiredPublicGuestShareArtifactsHandler:
        return PurgeExpiredPublicGuestShareArtifactsHandler(
            shares=shares,
            uow=uow,
            clock=clock,
        )

    @provide(scope=Scope.REQUEST)
    def revoke_public_guest_share_handler(
        self,
        shares: ClassroomPlannerShareArtifactRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
    ) -> RevokePublicGuestShareHandler:
        return RevokePublicGuestShareHandler(
            shares=shares,
            uow=uow,
            clock=clock,
        )

    @provide(scope=Scope.REQUEST)
    def classroom_planner_guest_upgrade_handler(
        self,
        uow: UnitOfWorkProtocol,
        rosters: RosterRepositoryProtocol,
        templates: RoomTemplateRepositoryProtocol,
        smart_rules: RosterSmartRuleRepositoryProtocol,
        drafts: PlanDraftRepositoryProtocol,
        seating_checkpoints: SeatingExportCheckpointRepositoryProtocol,
        grouping_checkpoints: GroupingExportCheckpointRepositoryProtocol,
        seating_export_jobs: SeatingExportJobRepositoryProtocol,
        grouping_export_jobs: GroupingExportJobRepositoryProtocol,
        guest_upgrade_repository: ClassroomPlannerGuestUpgradeRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> ClassroomPlannerGuestUpgradeHandler:
        return ClassroomPlannerGuestUpgradeHandler(
            uow=uow,
            rosters=rosters,
            templates=templates,
            smart_rules=smart_rules,
            drafts=drafts,
            seating_checkpoints=seating_checkpoints,
            grouping_checkpoints=grouping_checkpoints,
            seating_export_jobs=seating_export_jobs,
            grouping_export_jobs=grouping_export_jobs,
            guest_upgrade_repository=guest_upgrade_repository,
            clock=clock,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def classroom_planner_guest_upgrade_consumption_handler(
        self,
        guest_upgrade_repository: ClassroomPlannerGuestUpgradeRepositoryProtocol,
    ) -> GetClassroomPlannerGuestUpgradeConsumptionHandler:
        return GetClassroomPlannerGuestUpgradeConsumptionHandler(
            guest_upgrade_repository=guest_upgrade_repository,
        )

    @provide(scope=Scope.REQUEST)
    def classroom_planner_share_artifact_repository(
        self,
        session: AsyncSession,
    ) -> ClassroomPlannerShareArtifactRepositoryProtocol:
        return PostgreSQLClassroomPlannerShareArtifactRepository(session=session)

    @provide(scope=Scope.REQUEST)
    def classroom_planner_guest_upgrade_repository(
        self, session: AsyncSession
    ) -> ClassroomPlannerGuestUpgradeRepositoryProtocol:
        return PostgreSQLClassroomPlannerGuestUpgradeRepository(session=session)

    @provide(scope=Scope.APP)
    def classroom_planner_share_renderer(self) -> ClassroomPlannerShareRendererProtocol:
        return StaticClassroomPlannerShareRenderer()

    @provide(scope=Scope.APP)
    def classroom_planner_share_preview_renderer(
        self,
        settings: Settings,
    ) -> ClassroomPlannerSharePreviewRendererProtocol:
        return PlaywrightClassroomPlannerSharePreviewRenderer(
            settings=ClassroomPlannerSharePreviewRendererSettings(
                timeout_seconds=settings.CLASSROOM_SHARE_PREVIEW_TIMEOUT_SECONDS,
                max_concurrency=settings.CLASSROOM_SHARE_PREVIEW_MAX_CONCURRENCY,
            )
        )

    @provide(scope=Scope.APP)
    def classroom_planner_share_pdf_renderer(
        self,
        seating_poster_renderer: SeatingPosterRendererProtocol,
        seating_pdf_renderer: SeatingPdfRendererProtocol,
        grouping_pdf_renderer: GroupingPdfRendererProtocol,
    ) -> ClassroomPlannerSharePdfRendererProtocol:
        return ExportBackedClassroomPlannerSharePdfRenderer(
            seating_poster_renderer=seating_poster_renderer,
            seating_pdf_renderer=seating_pdf_renderer,
            grouping_pdf_renderer=grouping_pdf_renderer,
        )
