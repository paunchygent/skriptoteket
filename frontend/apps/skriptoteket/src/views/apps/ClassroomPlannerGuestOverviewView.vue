<script setup lang="ts">
/**
 * Classroom planner public guest view.
 *
 * This view hosts the public guest Klassrumskartan shell. It keeps the
 * browser-owned overview authoring surface, restores the checkpoint-3 guest
 * planner lane, and injects the guest-local planner state into the shared
 * grouping/seating presentation subtree.
 */

import { reactive } from "vue";
import { RouterLink, useRouter } from "vue-router";

import SystemMessage from "../../components/ui/SystemMessage.vue";
import CreateRosterModal from "./components/CreateRosterModal.vue";
import PlannerConfirmationDialog from "./components/PlannerConfirmationDialog.vue";
import PlannerClassWorkspace from "./components/PlannerClassWorkspace.vue";
import CreateRoomTemplateModal from "./components/CreateRoomTemplateModal.vue";
import ClassroomPlannerGuestWorkspaceShell from "./ClassroomPlannerGuestWorkspaceShell.vue";
import { provideClassroomState, type ClassroomStateLike } from "./useClassroomState";
import { useClassroomPlannerGuestController } from "./useClassroomPlannerGuestController";
import { usePublicGroupingExportFlow } from "./usePublicGroupingExportFlow";
import { usePublicSeatingExportFlow } from "./usePublicSeatingExportFlow";

const router = useRouter();
const guestController = useClassroomPlannerGuestController();
const providedGuestPlannerState = reactive(guestController.guestPlannerState);
const groupingExportFlow = usePublicGroupingExportFlow({
  plannerState: guestController.guestPlannerState,
  getSnapshot: guestController.ensureReadySnapshot,
  persistSnapshotMutation: guestController.persistSnapshotMutation,
});
const seatingExportFlow = usePublicSeatingExportFlow({
  plannerState: guestController.guestPlannerState,
  getSnapshot: guestController.ensureReadySnapshot,
  persistSnapshotMutation: guestController.persistSnapshotMutation,
});

provideClassroomState(providedGuestPlannerState as unknown as ClassroomStateLike);

async function exitPublicPlanner(): Promise<void> {
  await router.push({ name: "home" });
}
</script>

<template>
  <div
    class="w-full max-w-[90rem] self-center px-4 py-4 md:px-6"
    :class="guestController.currentScreen.value === 'planner' ? 'flex flex-1 min-h-0 flex-col gap-6' : 'space-y-6'"
  >
    <header class="border-b border-navy pb-4">
      <div>
        <h1 class="page-title">
          Klassrumskartan
        </h1>
      </div>
    </header>

    <SystemMessage
      v-if="!guestController.guestAuthoringClosed.value"
      id="classroom-planner-public-guest-message"
      :dismissible="false"
      model-value="guest-message"
      variant="info"
      data-test="public-guest-system-message"
    >
      Vissa funktioner kräver att du registrerar ett konto. Tryck
      <RouterLink
        to="/register"
        class="font-semibold underline"
      >
        här
      </RouterLink>
      för att skapa ett.
    </SystemMessage>

    <SystemMessage
      v-else
      id="classroom-planner-public-guest-closed-message"
      :dismissible="false"
      model-value="guest-closed-message"
      variant="warning"
      data-test="public-guest-authoring-closed-message"
    >
      Du har redan använt Klassrumskartan inloggad i den här webbläsaren. Därför går det inte att
      skapa nya klasser och klassrum här utan att logga in. Logga in för att fortsätta använda
      appen, eller
      <RouterLink
        to="/register"
        class="font-semibold underline"
      >
        skapa ett konto
      </RouterLink>
      om du inte har ett ännu.
    </SystemMessage>

    <div
      v-if="guestController.isBootstrapping.value"
      class="border border-navy bg-white px-4 py-12 text-center text-sm font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy shadow-brutal-sm"
    >
      Laddar planeringsmiljön...
    </div>

    <SystemMessage
      v-else-if="guestController.bootstrapError.value"
      :dismissible="false"
      :model-value="guestController.bootstrapError.value"
      variant="error"
    />

    <SystemMessage
      v-else-if="guestController.plannerActionError.value"
      :dismissible="false"
      :model-value="guestController.plannerActionError.value"
      variant="error"
    />

    <section
      v-else-if="guestController.guestAuthoringClosed.value"
      class="border border-navy bg-white px-4 py-12 text-center text-sm text-navy shadow-brutal-sm"
      data-test="public-guest-authoring-closed-state"
    >
      Det går inte att skapa nya klasser och klassrum i den här webbläsaren eftersom du redan har
      använt Klassrumskartan inloggad här. Logga in för att fortsätta använda appen.
    </section>

    <div
      v-else
      class="relative"
      :class="guestController.currentScreen.value === 'planner' ? 'flex min-h-0 flex-1 flex-col' : undefined"
    >
      <Transition name="planner-shell-swap">
        <PlannerClassWorkspace
          v-if="guestController.currentScreen.value === 'class-workspace'"
          :key="guestController.classWorkspaceSummary.value?.roster.id ?? 'guest-class-workspace'"
          :workspace-summary="guestController.classWorkspaceSummary.value"
          :available-rosters="guestController.availableRosters.value"
          :available-templates="guestController.availableTemplates.value"
          :selected-roster-id="guestController.selectedRosterId.value"
          :selected-template-id="guestController.selectedTemplateId.value"
          :is-loading-workspace="false"
          :visible-grouping-draft="null"
          :visible-seating-draft="null"
          :overview-capabilities="guestController.overviewCapabilities"
          @exit-app="void exitPublicPlanner()"
          @create-roster="guestController.openRosterCreate"
          @edit-roster="guestController.openSelectedRosterEdit"
          @delete-current-roster="guestController.openSelectedRosterDelete"
          @select-roster="void guestController.selectWorkspaceRoster($event)"
          @create-template="guestController.openTemplateCreate"
          @select-template="void guestController.selectWorkspaceTemplate($event)"
          @edit-current-template="guestController.openOverviewTemplateEdit"
          @delete-current-template="guestController.openSelectedTemplateDelete"
          @open-grouping="void guestController.openGroupingWorkspace()"
          @open-seating="void guestController.openSeatingWorkspace($event.templateId)"
          @open-rules="void guestController.openRulesWorkspace()"
        />

        <ClassroomPlannerGuestWorkspaceShell
          v-else
          key="guest-planner"
          class="flex-1 min-h-0"
          :available-rosters="guestController.availableRosters.value"
          :available-templates="guestController.availableTemplates.value"
          :selected-roster-id="guestController.selectedRosterId.value"
          :selected-template-id="guestController.selectedTemplateId.value"
          :initial-view="guestController.plannerInitialView.value"
          :grouping-export-busy="groupingExportFlow.isBusy.value"
          :grouping-export-status-label="groupingExportFlow.statusLabel.value"
          :grouping-export-error-message="groupingExportFlow.errorMessage.value"
          :seating-export-busy="seatingExportFlow.isBusy.value"
          :seating-export-status-label="seatingExportFlow.statusLabel.value"
          :seating-export-error-message="seatingExportFlow.errorMessage.value"
          @change-grouping-roster="void guestController.changeGroupingRoster($event)"
          @change-grouping-template="void guestController.changeGroupingTemplate($event)"
          @change-seating-template="void guestController.changeSeatingTemplate($event)"
          @new-grouping-draft="void guestController.startNewGroupingDraft()"
          @new-seating-draft="void guestController.startNewSeatingDraft($event)"
          @edit-roster="guestController.openSelectedRosterEdit"
          @export-grouping-default="void groupingExportFlow.startDefaultExport()"
          @export-grouping-option="void groupingExportFlow.startExport($event)"
          @export-seating-default="void seatingExportFlow.startDefaultExport()"
          @export-seating-option="void seatingExportFlow.startExport($event)"
          @edit-current-template="guestController.openOverviewTemplateEdit"
          @select-workspace-mode="void guestController.selectPlannerWorkspaceMode($event)"
          @exit-app="void exitPublicPlanner()"
        />
      </Transition>
    </div>

    <CreateRosterModal
      v-if="guestController.isRosterModalOpen.value"
      :roster="guestController.activeRosterModal.value"
      :import-preview-api-path="guestController.rosterImportPreviewApiPath"
      :save-roster="guestController.saveRoster"
      :delete-roster="guestController.deleteRoster"
      @close="guestController.closeRosterModal"
      @saved="guestController.applySavedRoster"
      @deleted="guestController.applyDeletedRoster"
    />

    <CreateRoomTemplateModal
      v-if="guestController.isTemplateModalOpen.value"
      :template="guestController.activeTemplateModal.value"
      :save-template="guestController.saveTemplate"
      :delete-template="guestController.deleteTemplate"
      @close="guestController.closeTemplateModal"
      @saved="guestController.applySavedTemplate"
      @deleted="guestController.applyDeletedTemplate"
    />

    <PlannerConfirmationDialog
      v-if="guestController.overviewDeleteRosterTarget.value"
      eyebrow="Ta bort klasslista"
      title="Är du säker?"
      :message="`Klasslistan ${guestController.overviewDeleteRosterTarget.value.name} tas bort från den publika arbetsytan i den här webbläsaren.`"
      confirm-label="Ta bort klasslista"
      :error-message="guestController.overviewDeleteRosterError.value"
      :is-submitting="guestController.isDeletingOverviewRoster.value"
      @cancel="guestController.closeOverviewRosterDelete"
      @confirm="void guestController.confirmOverviewRosterDelete()"
    />

    <PlannerConfirmationDialog
      v-if="guestController.overviewDeleteTemplateTarget.value"
      eyebrow="Ta bort klassrum"
      title="Är du säker?"
      :message="`Klassrummet ${guestController.overviewDeleteTemplateTarget.value.name} tas bort från den publika arbetsytan i den här webbläsaren.`"
      confirm-label="Ta bort klassrum"
      :error-message="guestController.overviewDeleteTemplateError.value"
      :is-submitting="guestController.isDeletingOverviewTemplate.value"
      @cancel="guestController.closeOverviewTemplateDelete"
      @confirm="void guestController.confirmOverviewTemplateDelete()"
    />
  </div>
</template>
