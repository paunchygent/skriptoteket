<script setup lang="ts">
/**
 * Classroom planner public guest overview view.
 *
 * This view is the checkpoint-2 public Klassrumskartan shell. It keeps the
 * same overview-first presentation language as the authenticated planner while
 * delegating public overview authoring to the browser-owned guest controller.
 */

import { RouterLink, useRouter } from "vue-router";

import SystemMessage from "../../components/ui/SystemMessage.vue";
import CreateRosterModal from "./components/CreateRosterModal.vue";
import PlannerConfirmationDialog from "./components/PlannerConfirmationDialog.vue";
import PlannerClassWorkspace from "./components/PlannerClassWorkspace.vue";
import CreateRoomTemplateModal from "./components/CreateRoomTemplateModal.vue";
import { useClassroomPlannerGuestController } from "./useClassroomPlannerGuestController";

const router = useRouter();
const {
  availableRosters,
  availableTemplates,
  selectedRosterId,
  selectedTemplateId,
  isBootstrapping,
  bootstrapError,
  plannerActionError,
  classWorkspaceSummary,
  overviewCapabilities,
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
  rosterImportPreviewApiPath,
  selectWorkspaceRoster,
  selectWorkspaceTemplate,
  openRosterCreate,
  closeRosterModal,
  openSelectedRosterEdit,
  openSelectedRosterDelete,
  openTemplateCreate,
  closeTemplateModal,
  openOverviewTemplateEdit,
  openSelectedTemplateDelete,
  closeOverviewRosterDelete,
  closeOverviewTemplateDelete,
  saveRoster,
  deleteRoster,
  saveTemplate,
  deleteTemplate,
  applySavedRoster,
  applyDeletedRoster,
  applySavedTemplate,
  applyDeletedTemplate,
  confirmOverviewRosterDelete,
  confirmOverviewTemplateDelete,
} = useClassroomPlannerGuestController();

async function exitPublicPlanner(): Promise<void> {
  await router.push({ name: "home" });
}
</script>

<template>
  <div class="w-full max-w-[90rem] self-center space-y-6 px-4 py-4 md:px-6">
    <header class="border-b border-navy pb-4">
      <div>
        <h1 class="page-title">
          Klassrumskartan
        </h1>
      </div>
    </header>

    <SystemMessage
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

    <div
      v-if="isBootstrapping"
      class="border border-navy bg-white px-4 py-12 text-center text-sm font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy shadow-brutal-sm"
    >
      Laddar planeringsmiljön...
    </div>

    <SystemMessage
      v-else-if="bootstrapError"
      :dismissible="false"
      :model-value="bootstrapError"
      variant="error"
    />

    <SystemMessage
      v-else-if="plannerActionError"
      :dismissible="false"
      :model-value="plannerActionError"
      variant="error"
    />

    <PlannerClassWorkspace
      v-else
      :workspace-summary="classWorkspaceSummary"
      :available-rosters="availableRosters"
      :available-templates="availableTemplates"
      :selected-roster-id="selectedRosterId"
      :selected-template-id="selectedTemplateId"
      :is-loading-workspace="false"
      :visible-grouping-draft="null"
      :visible-seating-draft="null"
      :overview-capabilities="overviewCapabilities"
      @exit-app="void exitPublicPlanner()"
      @create-roster="openRosterCreate"
      @edit-roster="openSelectedRosterEdit"
      @delete-current-roster="openSelectedRosterDelete"
      @select-roster="void selectWorkspaceRoster($event)"
      @create-template="openTemplateCreate"
      @select-template="void selectWorkspaceTemplate($event)"
      @edit-current-template="openOverviewTemplateEdit"
      @delete-current-template="openSelectedTemplateDelete"
    />

    <CreateRosterModal
      v-if="isRosterModalOpen"
      :roster="activeRosterModal"
      :import-preview-api-path="rosterImportPreviewApiPath"
      :save-roster="saveRoster"
      :delete-roster="deleteRoster"
      @close="closeRosterModal"
      @saved="applySavedRoster"
      @deleted="applyDeletedRoster"
    />

    <CreateRoomTemplateModal
      v-if="isTemplateModalOpen"
      :template="activeTemplateModal"
      :save-template="saveTemplate"
      :delete-template="deleteTemplate"
      @close="closeTemplateModal"
      @saved="applySavedTemplate"
      @deleted="applyDeletedTemplate"
    />

    <PlannerConfirmationDialog
      v-if="overviewDeleteRosterTarget"
      eyebrow="Ta bort klasslista"
      title="Är du säker?"
      :message="`Klasslistan ${overviewDeleteRosterTarget.name} tas bort från den publika arbetsytan i den här webbläsaren.`"
      confirm-label="Ta bort klasslista"
      :error-message="overviewDeleteRosterError"
      :is-submitting="isDeletingOverviewRoster"
      @cancel="closeOverviewRosterDelete"
      @confirm="void confirmOverviewRosterDelete()"
    />

    <PlannerConfirmationDialog
      v-if="overviewDeleteTemplateTarget"
      eyebrow="Ta bort klassrum"
      title="Är du säker?"
      :message="`Klassrummet ${overviewDeleteTemplateTarget.name} tas bort från den publika arbetsytan i den här webbläsaren.`"
      confirm-label="Ta bort klassrum"
      :error-message="overviewDeleteTemplateError"
      :is-submitting="isDeletingOverviewTemplate"
      @cancel="closeOverviewTemplateDelete"
      @confirm="void confirmOverviewTemplateDelete()"
    />
  </div>
</template>
