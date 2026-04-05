<script setup lang="ts">
/**
 * Classroom planner public guest overview view.
 *
 * This view is the checkpoint-1 public Klassrumskartan shell. It keeps the
 * same overview-first presentation language as the authenticated planner while
 * delegating all public state to the browser-owned guest snapshot controller.
 */

import { RouterLink, useRouter } from "vue-router";

import SystemMessage from "../../components/ui/SystemMessage.vue";
import PlannerClassWorkspace from "./components/PlannerClassWorkspace.vue";
import { useClassroomPlannerGuestOverviewShell } from "./useClassroomPlannerGuestOverviewShell";

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
  selectWorkspaceRoster,
  selectWorkspaceTemplate,
} = useClassroomPlannerGuestOverviewShell();

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
      @select-roster="void selectWorkspaceRoster($event)"
      @select-template="void selectWorkspaceTemplate($event)"
    />
  </div>
</template>
