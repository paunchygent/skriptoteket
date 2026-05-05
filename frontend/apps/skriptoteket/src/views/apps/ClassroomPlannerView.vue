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
  overviewDeleteRosterError,
  overviewDeleteTemplateError,
  isDeletingOverviewRoster,
  isDeletingOverviewTemplate,
  isSeatingLifecycleBusy,
  busySeatingHistoryDraftId,
  isGroupingExportBusy,
  groupingExportStatusLabel,
  groupingExportErrorMessage,
  isSeatingExportBusy,
  seatingExportStatusLabel,
  seatingExportErrorMessage,
  isGroupingShareBusy,
  isGroupingShareLoading,
  groupingShareStatusLabel,
  groupingShareErrorMessage,
  groupingShareCopiedId,
  groupingShareRevokingId,
  groupingShares,
  isSeatingShareBusy,
  isSeatingShareLoading,
  seatingShareStatusLabel,
  seatingShareErrorMessage,
  seatingShareCopiedId,
  seatingShareRevokingId,
  seatingShares,
  workspaceTransitionLabel,
  workspaceNotice,
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
  openRulesWorkspace,
  changeGroupingRoster,
  changeGroupingTemplate,
  changeSeatingTemplate,
  startNewGroupingDraft,
  startNewSeatingDraft,
  openGroupingHistoryDraft,
  deleteGroupingHistoryDraft,
  openSeatingHistoryDraft,
  deleteSeatingHistoryDraft,
  prepareOverviewDistributionScope,
  startOverviewDefaultGroupingExport,
  startOverviewGroupingExportOption,
  startOverviewGroupingShareLink,
  startOverviewDefaultSeatingExport,
  startOverviewSeatingExportOption,
  startOverviewSeatingShareLink,
  startDefaultGroupingExport,
  startGroupingExportOption,
  startDefaultSeatingExport,
  startSeatingExportOption,
  startGroupingShareLink,
  copyGroupingShareLink,
  revokeGroupingShareLink,
  startSeatingShareLink,
  copySeatingShareLink,
  revokeSeatingShareLink,
  selectPlannerWorkspaceMode,
  upsertRoster,
  removeRosterFromOverview,
  closeOverviewRosterDelete,
  upsertTemplate,
  removeTemplateFromOverview,
  closeOverviewTemplateDelete,
  confirmOverviewTemplateDelete,
  confirmOverviewRosterDelete,
  dismissWorkspaceNotice,
  closeExitConfirmation,
  confirmExitWithoutWaiting,
} = useClassroomPlannerRouteShell();
</script>

<template>
  <div
    class="classroom-planner-stage w-full max-w-[90rem] self-center"
    :class="currentScreen === 'planner' ? 'flex flex-1 min-h-0 flex-col gap-6' : 'space-y-6'"
  >
    <header class="border-b border-navy pb-4">
      <div>
        <h1 class="page-title">
          Klassrumskartan
        </h1>
      </div>
    </header>

    <div
      v-if="isBootstrapping"
      class="border border-navy bg-panel px-4 py-12 text-center text-sm font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy shadow-brutal-sm"
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

    <div
      class="relative"
      :class="currentScreen === 'planner' ? 'flex min-h-0 flex-1 flex-col' : undefined"
    >
      <Transition name="planner-shell-swap">
        <PlannerClassWorkspace
          v-if="!isBootstrapping && !bootstrapError && currentScreen === 'class-workspace'"
          :key="classWorkspaceSummary?.roster.id ?? 'empty-overview'"
          :workspace-summary="classWorkspaceSummary"
          :available-rosters="availableRosters"
          :available-templates="availableTemplates"
          :selected-roster-id="selectedRosterId"
          :selected-template-id="selectedWorkspaceTemplateId"
          :is-loading-workspace="isLoadingClassWorkspace"
          :transition-label="workspaceTransitionLabel"
          :visible-grouping-draft="visibleOverviewGroupingDraft"
          :visible-seating-draft="visibleOverviewSeatingDraft"
          :grouping-export-busy="isGroupingExportBusy"
          :grouping-export-error-message="groupingExportErrorMessage"
          :grouping-share-busy="isGroupingShareBusy"
          :grouping-share-loading="isGroupingShareLoading"
          :grouping-share-status-label="groupingShareStatusLabel"
          :grouping-share-error-message="groupingShareErrorMessage"
          :grouping-share-revoking-id="groupingShareRevokingId"
          :grouping-shares="groupingShares"
          :seating-export-busy="isSeatingExportBusy"
          :seating-export-error-message="seatingExportErrorMessage"
          :seating-share-busy="isSeatingShareBusy"
          :seating-share-loading="isSeatingShareLoading"
          :seating-share-status-label="seatingShareStatusLabel"
          :seating-share-error-message="seatingShareErrorMessage"
          :seating-share-revoking-id="seatingShareRevokingId"
          :seating-shares="seatingShares"
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
          @open-rules="void openRulesWorkspace()"
          @dismiss-grouping-draft="dismissOverviewGroupingDraft"
          @dismiss-seating-draft="dismissOverviewSeatingDraft"
          @prepare-overview-distribution="void prepareOverviewDistributionScope($event)"
          @export-overview-grouping-default="void startOverviewDefaultGroupingExport()"
          @export-overview-grouping-option="void startOverviewGroupingExportOption($event)"
          @share-overview-grouping-link="void startOverviewGroupingShareLink()"
          @copy-overview-grouping-share="void copyGroupingShareLink($event)"
          @revoke-overview-grouping-share="void revokeGroupingShareLink($event)"
          @export-overview-seating-default="void startOverviewDefaultSeatingExport()"
          @export-overview-seating-option="void startOverviewSeatingExportOption($event)"
          @share-overview-seating-link="void startOverviewSeatingShareLink()"
          @copy-overview-seating-share="void copySeatingShareLink($event)"
          @revoke-overview-seating-share="void revokeSeatingShareLink($event)"
        />

        <PlannerWorkspaceShell
          v-else-if="!isBootstrapping && !bootstrapError && currentScreen === 'planner'"
          key="planner"
          class="flex-1 min-h-0"
          :available-rosters="availableRosters"
          :available-templates="availableTemplates"
          :selected-roster-id="selectedRosterId"
          :selected-workspace-template-id="selectedWorkspaceTemplateId"
          :initial-view="plannerInitialView"
          :workspace-summary="classWorkspaceSummary"
          :seating-lifecycle-busy="isSeatingLifecycleBusy"
          :seating-history-busy-draft-id="busySeatingHistoryDraftId"
          :grouping-export-busy="isGroupingExportBusy"
          :grouping-export-status-label="groupingExportStatusLabel"
          :grouping-export-error-message="groupingExportErrorMessage"
          :seating-export-busy="isSeatingExportBusy"
          :seating-export-status-label="seatingExportStatusLabel"
          :seating-export-error-message="seatingExportErrorMessage"
          :grouping-share-busy="isGroupingShareBusy"
          :grouping-share-loading="isGroupingShareLoading"
          :grouping-share-status-label="groupingShareStatusLabel"
          :grouping-share-error-message="groupingShareErrorMessage"
          :grouping-share-copied-id="groupingShareCopiedId"
          :grouping-share-revoking-id="groupingShareRevokingId"
          :grouping-shares="groupingShares"
          :seating-share-busy="isSeatingShareBusy"
          :seating-share-loading="isSeatingShareLoading"
          :seating-share-status-label="seatingShareStatusLabel"
          :seating-share-error-message="seatingShareErrorMessage"
          :seating-share-copied-id="seatingShareCopiedId"
          :seating-share-revoking-id="seatingShareRevokingId"
          :seating-shares="seatingShares"
          :transition-label="workspaceTransitionLabel"
          :workspace-notice="workspaceNotice"
          @change-grouping-roster="void changeGroupingRoster($event)"
          @change-grouping-template="void changeGroupingTemplate($event)"
          @change-seating-template="void changeSeatingTemplate($event)"
          @new-grouping-draft="void startNewGroupingDraft($event)"
          @new-seating-draft="void startNewSeatingDraft($event)"
          @export-grouping-default="void startDefaultGroupingExport()"
          @export-grouping-option="void startGroupingExportOption($event)"
          @share-grouping-link="void startGroupingShareLink()"
          @copy-grouping-share="void copyGroupingShareLink($event)"
          @revoke-grouping-share="void revokeGroupingShareLink($event)"
          @export-seating-default="void startDefaultSeatingExport()"
          @export-seating-option="void startSeatingExportOption($event)"
          @share-seating-link="void startSeatingShareLink()"
          @copy-seating-share="void copySeatingShareLink($event)"
          @revoke-seating-share="void revokeSeatingShareLink($event)"
          @edit-roster="openSelectedRosterEdit"
          @open-grouping-history-draft="void openGroupingHistoryDraft($event)"
          @delete-grouping-history-draft="void deleteGroupingHistoryDraft($event)"
          @open-seating-history-draft="void openSeatingHistoryDraft($event)"
          @delete-seating-history-draft="void deleteSeatingHistoryDraft($event)"
          @edit-current-template="openOverviewTemplateEdit"
          @open-rules="void openRulesWorkspace()"
          @select-workspace-mode="void selectPlannerWorkspaceMode($event)"
          @dismiss-workspace-notice="dismissWorkspaceNotice"
          @exit-app="void exitPlannerApp()"
        />
      </Transition>
    </div>

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
      :message="`Klasslistan ${overviewDeleteRosterTarget.name} tas bort från översikten tillsammans med alla beroende grupp- och sittutkast för den klassen.`"
      confirm-label="Ta bort klasslista"
      :error-message="overviewDeleteRosterError"
      :is-submitting="isDeletingOverviewRoster"
      @cancel="closeOverviewRosterDelete"
      @confirm="void confirmOverviewRosterDelete()"
      @dismiss-error="overviewDeleteRosterError = null"
    />

    <PlannerConfirmationDialog
      v-if="overviewDeleteTemplateTarget"
      eyebrow="Ta bort klassrum"
      title="Är du säker?"
      :message="`Klassrummet ${overviewDeleteTemplateTarget.name} tas bort från översikten tillsammans med alla beroende grupp- och sittutkast som använder klassrummet.`"
      confirm-label="Ta bort klassrum"
      :error-message="overviewDeleteTemplateError"
      :is-submitting="isDeletingOverviewTemplate"
      @cancel="closeOverviewTemplateDelete"
      @confirm="void confirmOverviewTemplateDelete()"
      @dismiss-error="overviewDeleteTemplateError = null"
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

<style scoped>
.planner-shell-swap-enter-active,
.planner-shell-swap-leave-active {
  transition: opacity var(--huleedu-duration-fast) var(--huleedu-ease-default);
}

.planner-shell-swap-enter-from,
.planner-shell-swap-leave-to {
  opacity: 0;
}

.planner-shell-swap-leave-active {
  inset: 0;
  pointer-events: none;
  position: absolute;
  width: 100%;
}
</style>
