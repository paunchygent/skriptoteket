"""DI bindings for classroom planner exports.

Seating and grouping export job handlers, finalizers, checkpoint recorders,
export repositories, and the PDF, XLSX, and poster renderers.
"""

from __future__ import annotations

from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.application.curated_apps.classroom_planner import (
    CreateGroupingExportJobHandler,
    CreateSeatingExportJobHandler,
    DownloadGroupingExportJobHandler,
    DownloadSeatingExportJobHandler,
    GetGroupingExportJobHandler,
    GetRecoverableGroupingExportJobForDraftHandler,
    GetRecoverableSeatingExportJobForDraftHandler,
    GetSeatingExportJobHandler,
    GroupingExportJobFinalizer,
    PrepareGroupingExportHandler,
    PrepareSeatingExportHandler,
    RunPublicGroupingExportHandler,
    RunPublicSeatingExportHandler,
    SeatingExportJobFinalizer,
)
from skriptoteket.application.curated_apps.classroom_planner.handlers.checkpoint_recorders import (
    GroupingCheckpointRecorder,
    SeatingCheckpointRecorder,
)
from skriptoteket.config import Settings
from skriptoteket.infrastructure.curated_apps.apps.classroom_planner.grouping_pdf_renderer import (
    GroupingPdfRenderer,
)
from skriptoteket.infrastructure.curated_apps.apps.classroom_planner.grouping_xlsx_renderer import (
    GroupingXlsxRenderer,
)
from skriptoteket.infrastructure.curated_apps.apps.classroom_planner.poster_renderer import (
    BrutalistPosterRenderer,
)
from skriptoteket.infrastructure.curated_apps.apps.classroom_planner.seating_pdf_renderer import (
    WeasyPrintSeatingPdfRenderer,
)
from skriptoteket.infrastructure.curated_apps.apps.classroom_planner.seating_xlsx_renderer import (
    SeatingXlsxRenderer,
)
from skriptoteket.infrastructure.repositories.classroom_planner_export_jobs import (
    PostgreSQLSeatingExportJobRepository,
)
from skriptoteket.infrastructure.repositories.classroom_planner_grouping_export_checkpoints import (
    PostgreSQLGroupingExportCheckpointRepository,
)
from skriptoteket.infrastructure.repositories.classroom_planner_grouping_export_jobs import (
    PostgreSQLGroupingExportJobRepository,
)
from skriptoteket.infrastructure.repositories.classroom_planner_seating_export_checkpoints import (
    PostgreSQLSeatingExportCheckpointRepository,
)
from skriptoteket.protocols.classroom_planner import (
    GroupingExportCheckpointRepositoryProtocol,
    PlanDraftRepositoryProtocol,
    RoomTemplateRepositoryProtocol,
    RosterRepositoryProtocol,
    SeatingExportCheckpointRepositoryProtocol,
)
from skriptoteket.protocols.classroom_planner_exports import (
    GroupingExportJobRepositoryProtocol,
    GroupingPdfRendererProtocol,
    GroupingXlsxRendererProtocol,
    SeatingExportJobRepositoryProtocol,
    SeatingPdfRendererProtocol,
    SeatingPosterRendererProtocol,
    SeatingXlsxRendererProtocol,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from skriptoteket.protocols.vault import (
    VaultFileRepositoryProtocol,
    VaultStorageProtocol,
    VaultUsageRepositoryProtocol,
)


class ClassroomPlannerExportProvider(Provider):
    """Provide classroom planner export handlers, repositories, and renderers."""

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
        pdf_renderer: SeatingPdfRendererProtocol,
        poster_renderer: SeatingPosterRendererProtocol,
        xlsx_renderer: SeatingXlsxRendererProtocol,
        finalizer: SeatingExportJobFinalizer,
        vault_files: VaultFileRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> CreateSeatingExportJobHandler:
        return CreateSeatingExportJobHandler(
            prepare=prepare,
            jobs=jobs,
            pdf_renderer=pdf_renderer,
            poster_renderer=poster_renderer,
            xlsx_renderer=xlsx_renderer,
            finalizer=finalizer,
            vault_files=vault_files,
            uow=uow,
            clock=clock,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def grouping_export_job_handler(
        self,
        prepare: PrepareGroupingExportHandler,
        jobs: GroupingExportJobRepositoryProtocol,
        pdf_renderer: GroupingPdfRendererProtocol,
        xlsx_renderer: GroupingXlsxRendererProtocol,
        finalizer: GroupingExportJobFinalizer,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> CreateGroupingExportJobHandler:
        return CreateGroupingExportJobHandler(
            prepare=prepare,
            jobs=jobs,
            pdf_renderer=pdf_renderer,
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
        checkpoint_recorder: SeatingCheckpointRecorder,
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
            checkpoint_recorder=checkpoint_recorder,
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
        checkpoint_recorder: GroupingCheckpointRecorder,
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
            checkpoint_recorder=checkpoint_recorder,
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
        uow: UnitOfWorkProtocol,
    ) -> GetSeatingExportJobHandler:
        return GetSeatingExportJobHandler(
            jobs=jobs,
            vault_files=vault_files,
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
        uow: UnitOfWorkProtocol,
    ) -> GetRecoverableSeatingExportJobForDraftHandler:
        return GetRecoverableSeatingExportJobForDraftHandler(
            jobs=jobs,
            vault_files=vault_files,
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
    def run_public_grouping_export_handler(
        self,
        prepare: PrepareGroupingExportHandler,
        pdf_renderer: GroupingPdfRendererProtocol,
        xlsx_renderer: GroupingXlsxRendererProtocol,
        clock: ClockProtocol,
    ) -> RunPublicGroupingExportHandler:
        return RunPublicGroupingExportHandler(
            prepare=prepare,
            pdf_renderer=pdf_renderer,
            xlsx_renderer=xlsx_renderer,
            clock=clock,
        )

    @provide(scope=Scope.REQUEST)
    def run_public_seating_export_handler(
        self,
        prepare: PrepareSeatingExportHandler,
        pdf_renderer: SeatingPdfRendererProtocol,
        poster_renderer: SeatingPosterRendererProtocol,
        xlsx_renderer: SeatingXlsxRendererProtocol,
        clock: ClockProtocol,
    ) -> RunPublicSeatingExportHandler:
        return RunPublicSeatingExportHandler(
            prepare=prepare,
            pdf_renderer=pdf_renderer,
            poster_renderer=poster_renderer,
            xlsx_renderer=xlsx_renderer,
            clock=clock,
        )

    @provide(scope=Scope.REQUEST)
    def seating_export_job_repository(
        self, session: AsyncSession
    ) -> SeatingExportJobRepositoryProtocol:
        return PostgreSQLSeatingExportJobRepository(session=session)

    @provide(scope=Scope.REQUEST)
    def seating_export_checkpoint_repository(
        self, session: AsyncSession
    ) -> SeatingExportCheckpointRepositoryProtocol:
        return PostgreSQLSeatingExportCheckpointRepository(session=session)

    @provide(scope=Scope.REQUEST)
    def seating_checkpoint_recorder(
        self,
        checkpoints: SeatingExportCheckpointRepositoryProtocol,
    ) -> SeatingCheckpointRecorder:
        return SeatingCheckpointRecorder(checkpoints=checkpoints)

    @provide(scope=Scope.REQUEST)
    def grouping_export_job_repository(
        self, session: AsyncSession
    ) -> GroupingExportJobRepositoryProtocol:
        return PostgreSQLGroupingExportJobRepository(session=session)

    @provide(scope=Scope.REQUEST)
    def grouping_export_checkpoint_repository(
        self, session: AsyncSession
    ) -> GroupingExportCheckpointRepositoryProtocol:
        return PostgreSQLGroupingExportCheckpointRepository(session=session)

    @provide(scope=Scope.REQUEST)
    def grouping_checkpoint_recorder(
        self,
        checkpoints: GroupingExportCheckpointRepositoryProtocol,
    ) -> GroupingCheckpointRecorder:
        return GroupingCheckpointRecorder(checkpoints=checkpoints)

    @provide(scope=Scope.APP)
    def seating_poster_renderer(self) -> SeatingPosterRendererProtocol:
        return BrutalistPosterRenderer()

    @provide(scope=Scope.APP)
    def seating_pdf_renderer(self) -> SeatingPdfRendererProtocol:
        return WeasyPrintSeatingPdfRenderer()

    @provide(scope=Scope.APP)
    def seating_xlsx_renderer(self) -> SeatingXlsxRendererProtocol:
        return SeatingXlsxRenderer()

    @provide(scope=Scope.APP)
    def grouping_xlsx_renderer(self) -> GroupingXlsxRendererProtocol:
        return GroupingXlsxRenderer()

    @provide(scope=Scope.APP)
    def grouping_pdf_renderer(self) -> GroupingPdfRendererProtocol:
        return GroupingPdfRenderer()
