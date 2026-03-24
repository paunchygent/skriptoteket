/**
 * Classroom planner route-shell orchestration.
 *
 * This composable coordinates Klassrumskartan's overview-first shell while the
 * extracted helper modules own workspace transitions, overview CRUD flows, and
 * exit-to-origin behavior.
 */

import { onMounted, ref } from "vue";
import { storeToRefs } from "pinia";
import { useRouter } from "vue-router";

import { fetchClassroomPlannerCatalog } from "./classroomPlannerCatalogApi";
import { useClassroomPlannerOverviewStore } from "./classroomPlannerOverviewStore";
import { normalizeClassroomPlannerUiError } from "./classroomPlannerRouteShellErrors";
import { createClassroomPlannerExitFlow } from "./classroomPlannerRouteShellExit";
import { createClassroomPlannerOverviewCrudFlow } from "./classroomPlannerRouteShellOverviewCrud";
import { createClassroomPlannerWorkspaceFlow } from "./classroomPlannerRouteShellWorkspace";
import { useSeatingExportFlow } from "./useSeatingExportFlow";
import { useClassroomState } from "./useClassroomState";

export function useClassroomPlannerRouteShell() {
  const router = useRouter();
  const plannerState = useClassroomState();
  const overviewStore = useClassroomPlannerOverviewStore();

  overviewStore.reset();

  const {
    availableRosters,
    availableTemplates,
    selectedRosterId,
    selectedWorkspaceTemplateId,
    currentScreen,
    plannerInitialView,
    isBootstrapping,
    isLoadingClassWorkspace,
    bootstrapError,
    plannerActionError,
    classWorkspaceSummary,
    visibleOverviewGroupingDraft,
    visibleOverviewSeatingDraft,
  } = storeToRefs(overviewStore);

  const isSeatingLifecycleBusy = ref(false);
  const busySeatingHistoryDraftId = ref<string | null>(null);

  async function fetchCatalog(): Promise<void> {
    const catalog = await fetchClassroomPlannerCatalog();
    overviewStore.setCatalog(catalog.rosters, catalog.templates);
  }

  async function loadClassWorkspaceSummary(rosterId: string): Promise<void> {
    classWorkspaceSummary.value = await plannerState.getClassWorkspaceSummary(rosterId);
  }

  async function openClassWorkspace(rosterId: string): Promise<void> {
    plannerActionError.value = null;
    selectedRosterId.value = rosterId;
    overviewStore.dismissedOverviewGroupingDraftId = null;
    overviewStore.dismissedOverviewSeatingDraftId = null;
    isLoadingClassWorkspace.value = true;
    try {
      await loadClassWorkspaceSummary(rosterId);
      overviewStore.syncWorkspaceTemplateSelection();
      currentScreen.value = "class-workspace";
    } catch (error: unknown) {
      classWorkspaceSummary.value = null;
      selectedWorkspaceTemplateId.value = null;
      plannerActionError.value = normalizeClassroomPlannerUiError(
        error,
        "Kunde inte öppna klassarbetsytan just nu.",
      );
    } finally {
      isLoadingClassWorkspace.value = false;
    }
  }

  async function openInitialHomeWorkspace(preferredRosterId: string | null): Promise<void> {
    const nextRosterId = overviewStore.resolveHomeRosterId(preferredRosterId);
    if (!nextRosterId) {
      overviewStore.clearOverviewWorkspaceState();
      currentScreen.value = "class-workspace";
      return;
    }

    await openClassWorkspace(nextRosterId);
  }

  async function refreshClassWorkspaceSummaryForSelectedRoster(): Promise<void> {
    const rosterId = plannerState.roster?.id ?? selectedRosterId.value;
    if (!rosterId) {
      return;
    }

    classWorkspaceSummary.value = await plannerState.getClassWorkspaceSummary(rosterId);
    overviewStore.syncWorkspaceTemplateSelection({ preserveCurrent: true });
  }

  const workspaceFlow = createClassroomPlannerWorkspaceFlow(
    {
      selectedRosterId,
      currentScreen,
      plannerInitialView,
      plannerActionError,
      classWorkspaceSummary,
      isSeatingLifecycleBusy,
      busySeatingHistoryDraftId,
    },
    {
      loadClassWorkspaceSummary,
      refreshClassWorkspaceSummaryForSelectedRoster,
      openInitialHomeWorkspace,
      syncWorkspaceTemplateSelection: overviewStore.syncWorkspaceTemplateSelection,
    },
    plannerState,
  );

  const overviewCrudFlow = createClassroomPlannerOverviewCrudFlow(
    {
      availableRosters,
      availableTemplates,
      selectedRosterId,
      selectedWorkspaceTemplateId,
      currentScreen,
      classWorkspaceSummary,
      plannerActionError,
    },
    {
      openClassWorkspace,
      openInitialHomeWorkspace,
      syncWorkspaceTemplateSelection: overviewStore.syncWorkspaceTemplateSelection,
    },
  );

  const exitFlow = createClassroomPlannerExitFlow({
    plannerActionError,
    currentScreen,
    router,
    plannerState,
    clearOverviewWorkspaceState: overviewStore.clearOverviewWorkspaceState,
  });
  const seatingExportFlow = useSeatingExportFlow({
    plannerState,
  });

  onMounted(async () => {
    isBootstrapping.value = true;
    bootstrapError.value = null;
    try {
      exitFlow.initializeEntryOrigin();
      const [, resumableDraft] = await Promise.all([
        fetchCatalog(),
        plannerState.getResumableDraft(),
      ]);
      await openInitialHomeWorkspace(resumableDraft?.draft.roster_id ?? null);
    } catch (error: unknown) {
      bootstrapError.value = error instanceof Error ? error.message : "Kunde inte ladda Klassrumskartan.";
    } finally {
      isBootstrapping.value = false;
    }
  });

  return {
    availableRosters,
    availableTemplates,
    selectedRosterId,
    selectedWorkspaceTemplateId,
    currentScreen,
    plannerInitialView,
    isBootstrapping,
    isLoadingClassWorkspace,
    bootstrapError,
    plannerActionError,
    classWorkspaceSummary,
    visibleOverviewGroupingDraft,
    visibleOverviewSeatingDraft,
    isRosterModalOpen: overviewCrudFlow.isRosterModalOpen,
    isTemplateModalOpen: overviewCrudFlow.isTemplateModalOpen,
    activeRosterModal: overviewCrudFlow.activeRosterModal,
    activeTemplateModal: overviewCrudFlow.activeTemplateModal,
    overviewDeleteRosterTarget: overviewCrudFlow.overviewDeleteRosterTarget,
    overviewDeleteTemplateTarget: overviewCrudFlow.overviewDeleteTemplateTarget,
    isDeletingOverviewRoster: overviewCrudFlow.isDeletingOverviewRoster,
    isDeletingOverviewTemplate: overviewCrudFlow.isDeletingOverviewTemplate,
    isSeatingLifecycleBusy,
    busySeatingHistoryDraftId,
    isSeatingExportBusy: seatingExportFlow.isBusy,
    seatingExportStatusLabel: seatingExportFlow.statusLabel,
    seatingExportErrorMessage: seatingExportFlow.errorMessage,
    canDownloadLatestSeatingExport: seatingExportFlow.canDownloadLatest,
    isExitConfirmationOpen: exitFlow.isExitConfirmationOpen,
    isExitingWithoutSave: exitFlow.isExitingWithoutSave,
    dismissOverviewGroupingDraft: overviewStore.dismissOverviewGroupingDraft,
    dismissOverviewSeatingDraft: overviewStore.dismissOverviewSeatingDraft,
    exitPlannerApp: exitFlow.exitPlannerApp,
    openRosterCreate: overviewCrudFlow.openRosterCreate,
    closeRosterModal: overviewCrudFlow.closeRosterModal,
    openSelectedRosterEdit: overviewCrudFlow.openSelectedRosterEdit,
    openSelectedRosterDelete: overviewCrudFlow.openSelectedRosterDelete,
    selectWorkspaceRoster: overviewCrudFlow.selectWorkspaceRoster,
    openTemplateCreate: overviewCrudFlow.openTemplateCreate,
    closeTemplateModal: overviewCrudFlow.closeTemplateModal,
    selectWorkspaceTemplate: overviewCrudFlow.selectWorkspaceTemplate,
    openOverviewTemplateEdit: overviewCrudFlow.openOverviewTemplateEdit,
    openSelectedTemplateDelete: overviewCrudFlow.openSelectedTemplateDelete,
    openGroupingWorkspace: workspaceFlow.openGroupingWorkspace,
    openSeatingWorkspace: workspaceFlow.openSeatingWorkspace,
    changeGroupingTemplate: workspaceFlow.changeGroupingTemplate,
    changeSeatingTemplate: workspaceFlow.changeSeatingTemplate,
    startNewGroupingDraft: workspaceFlow.startNewGroupingDraft,
    startNewSeatingDraft: workspaceFlow.startNewSeatingDraft,
    openGroupingHistoryDraft: workspaceFlow.openGroupingHistoryDraft,
    deleteGroupingHistoryDraft: workspaceFlow.deleteGroupingHistoryDraft,
    openSeatingHistoryDraft: workspaceFlow.openSeatingHistoryDraft,
    deleteSeatingHistoryDraft: workspaceFlow.deleteSeatingHistoryDraft,
    startDefaultSeatingExport: seatingExportFlow.startDefaultExport,
    startSeatingExportOption: seatingExportFlow.startExportOption,
    downloadLatestSeatingExport: seatingExportFlow.downloadLatest,
    selectPlannerWorkspaceMode: workspaceFlow.selectPlannerWorkspaceMode,
    upsertRoster: overviewCrudFlow.upsertRoster,
    removeRosterFromOverview: overviewCrudFlow.removeRosterFromOverview,
    closeOverviewRosterDelete: overviewCrudFlow.closeOverviewRosterDelete,
    upsertTemplate: overviewCrudFlow.upsertTemplate,
    removeTemplateFromOverview: overviewCrudFlow.removeTemplateFromOverview,
    closeOverviewTemplateDelete: overviewCrudFlow.closeOverviewTemplateDelete,
    confirmOverviewTemplateDelete: overviewCrudFlow.confirmOverviewTemplateDelete,
    confirmOverviewRosterDelete: overviewCrudFlow.confirmOverviewRosterDelete,
    closeExitConfirmation: exitFlow.closeExitConfirmation,
    confirmExitWithoutWaiting: exitFlow.confirmExitWithoutWaiting,
  };
}
