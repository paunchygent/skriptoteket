<script setup lang="ts">
/**
 * Klassrumskartan planner root view.
 *
 * This view stays intentionally thin. It composes the overview shell, planner
 * shell, and modal surfaces while the extracted route-shell composable owns the
 * overview-first boot flow, shell transitions, and exit-to-origin behavior.
 */

import CreateRosterModal from "./components/CreateRosterModal.vue";
import PlannerClassWorkspace from "./components/PlannerClassWorkspace.vue";
import PlannerConfirmationDialog from "./components/PlannerConfirmationDialog.vue";
import CreateRoomTemplateModal from "./components/CreateRoomTemplateModal.vue";
import PlannerWorkspaceShell from "./components/PlannerWorkspaceShell.vue";
import { useClassroomPlannerRouteShell } from "./useClassroomPlannerRouteShell";

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
  isRosterModalOpen,
  isTemplateModalOpen,
  activeRosterModal,
  activeTemplateModal,
  overviewDeleteRosterTarget,
  overviewDeleteTemplateTarget,
  isDeletingOverviewRoster,
  isDeletingOverviewTemplate,
  isSeatingLifecycleBusy,
  busySeatingHistoryDraftId,
  isSeatingExportBusy,
  seatingExportStatusLabel,
  seatingExportErrorMessage,
  canDownloadLatestSeatingExport,
  isExitConfirmationOpen,
  isExitingWithoutSave,
  dismissOverviewGroupingDraft,
  dismissOverviewSeatingDraft,
  exitPlannerApp,
  openRosterCreate,
  closeRosterModal,
  openSelectedRosterEdit,
  openSelectedRosterDelete,
  selectWorkspaceRoster,
  openTemplateCreate,
  closeTemplateModal,
  selectWorkspaceTemplate,
  openOverviewTemplateEdit,
  openSelectedTemplateDelete,
  openGroupingWorkspace,
  openSeatingWorkspace,
  changeGroupingTemplate,
  changeSeatingTemplate,
  startNewGroupingDraft,
  startNewSeatingDraft,
  openGroupingHistoryDraft,
  deleteGroupingHistoryDraft,
  openSeatingHistoryDraft,
  deleteSeatingHistoryDraft,
  startDefaultSeatingExport,
  startSeatingExportOption,
  downloadLatestSeatingExport,
  selectPlannerWorkspaceMode,
  upsertRoster,
  removeRosterFromOverview,
  closeOverviewRosterDelete,
  upsertTemplate,
  removeTemplateFromOverview,
  closeOverviewTemplateDelete,
  confirmOverviewTemplateDelete,
  confirmOverviewRosterDelete,
  closeExitConfirmation,
  confirmExitWithoutWaiting,
} = useClassroomPlannerRouteShell();
</script>

<template>
  <div class="mx-auto max-w-[90rem] space-y-6 px-4 py-4 md:px-6">
    <header class="border-b border-navy pb-4">
      <div class="space-y-1">
        <p class="text-[11px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
          Curated App
        </p>
        <h1 class="font-serif text-4xl text-navy md:text-5xl">
          Klassrumskartan
        </h1>
        <p class="max-w-[40rem] text-sm leading-relaxed text-navy/70">
          Arbeta vidare från översikten och öppna grupper eller sittplatser när du behöver dem.
        </p>
      </div>
    </header>

    <div
      v-if="isBootstrapping"
      class="border border-navy bg-white px-4 py-12 text-center text-sm font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy shadow-brutal-sm"
    >
      Laddar planeringsmiljön...
    </div>

    <div
      v-else-if="bootstrapError"
      class="system-message system-message-error"
    >
      <div class="system-message-content">
        {{ bootstrapError }}
      </div>
    </div>

    <div
      v-else-if="plannerActionError"
      class="system-message system-message-error"
    >
      <div class="system-message-content">
        {{ plannerActionError }}
      </div>
    </div>

    <PlannerClassWorkspace
      v-if="!isBootstrapping && !bootstrapError && currentScreen === 'class-workspace'"
      :key="classWorkspaceSummary?.roster.id ?? 'empty-overview'"
      :workspace-summary="classWorkspaceSummary"
      :available-rosters="availableRosters"
      :available-templates="availableTemplates"
      :selected-roster-id="selectedRosterId"
      :selected-template-id="selectedWorkspaceTemplateId"
      :is-loading-workspace="isLoadingClassWorkspace"
      :visible-grouping-draft="visibleOverviewGroupingDraft"
      :visible-seating-draft="visibleOverviewSeatingDraft"
      @exit-app="void exitPlannerApp()"
      @create-roster="openRosterCreate"
      @edit-roster="openSelectedRosterEdit"
      @delete-current-roster="openSelectedRosterDelete"
      @select-roster="selectWorkspaceRoster"
      @create-template="openTemplateCreate"
      @select-template="selectWorkspaceTemplate"
      @edit-current-template="openOverviewTemplateEdit"
      @delete-current-template="openSelectedTemplateDelete"
      @open-grouping="void openGroupingWorkspace($event)"
      @open-seating="void openSeatingWorkspace($event)"
      @dismiss-grouping-draft="dismissOverviewGroupingDraft"
      @dismiss-seating-draft="dismissOverviewSeatingDraft"
    />

    <PlannerWorkspaceShell
      v-if="!isBootstrapping && !bootstrapError && currentScreen === 'planner'"
      :available-templates="availableTemplates"
      :initial-view="plannerInitialView"
      :workspace-summary="classWorkspaceSummary"
      :seating-lifecycle-busy="isSeatingLifecycleBusy"
      :seating-history-busy-draft-id="busySeatingHistoryDraftId"
      :seating-export-busy="isSeatingExportBusy"
      :seating-export-status-label="seatingExportStatusLabel"
      :seating-export-error-message="seatingExportErrorMessage"
      :can-download-latest-seating-export="canDownloadLatestSeatingExport"
      @change-grouping-template="void changeGroupingTemplate($event)"
      @change-seating-template="void changeSeatingTemplate($event)"
      @new-grouping-draft="void startNewGroupingDraft($event)"
      @new-seating-draft="void startNewSeatingDraft($event)"
      @export-seating-default="void startDefaultSeatingExport()"
      @export-seating-option="void startSeatingExportOption($event)"
      @download-latest-seating-export="void downloadLatestSeatingExport()"
      @edit-roster="openSelectedRosterEdit"
      @open-grouping-history-draft="void openGroupingHistoryDraft($event)"
      @delete-grouping-history-draft="void deleteGroupingHistoryDraft($event)"
      @open-seating-history-draft="void openSeatingHistoryDraft($event)"
      @delete-seating-history-draft="void deleteSeatingHistoryDraft($event)"
      @edit-current-template="openOverviewTemplateEdit"
      @select-workspace-mode="void selectPlannerWorkspaceMode($event)"
      @exit-app="void exitPlannerApp()"
    />

    <CreateRosterModal
      v-if="isRosterModalOpen"
      :roster="activeRosterModal"
      @close="closeRosterModal"
      @saved="void upsertRoster($event)"
      @deleted="void removeRosterFromOverview($event)"
    />

    <CreateRoomTemplateModal
      v-if="isTemplateModalOpen"
      :template="activeTemplateModal"
      @close="closeTemplateModal"
      @saved="upsertTemplate($event)"
      @deleted="removeTemplateFromOverview($event)"
    />

    <PlannerConfirmationDialog
      v-if="overviewDeleteRosterTarget"
      eyebrow="Ta bort klasslista"
      title="Är du säker?"
      :message="`Klasslistan ${overviewDeleteRosterTarget.name} tas bort från översikten. Aktiva utkast som fortfarande använder klassen skyddas av backend-reglerna och kan stoppa borttagningen.`"
      confirm-label="Ta bort klasslista"
      :is-submitting="isDeletingOverviewRoster"
      @cancel="closeOverviewRosterDelete"
      @confirm="void confirmOverviewRosterDelete()"
    />

    <PlannerConfirmationDialog
      v-if="overviewDeleteTemplateTarget"
      eyebrow="Ta bort klassrum"
      title="Är du säker?"
      :message="`Klassrummet ${overviewDeleteTemplateTarget.name} tas bort från översikten. Utkast som fortfarande använder klassrummet skyddas av backend-reglerna och kan stoppa borttagningen.`"
      confirm-label="Ta bort klassrum"
      :is-submitting="isDeletingOverviewTemplate"
      @cancel="closeOverviewTemplateDelete"
      @confirm="void confirmOverviewTemplateDelete()"
    />

    <PlannerConfirmationDialog
      v-if="isExitConfirmationOpen"
      eyebrow="Avsluta"
      title="Lämna Klassrumskartan?"
      message="Den senaste autosparningen blev inte klar i tid. Om du lämnar nu kan de senaste ändringarna gå förlorade."
      confirm-label="Avsluta ändå"
      :is-submitting="isExitingWithoutSave"
      @cancel="closeExitConfirmation"
      @confirm="void confirmExitWithoutWaiting()"
    />
  </div>
</template>
