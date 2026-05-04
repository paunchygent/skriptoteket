<script setup lang="ts">
/**
 * Desktop overview setup panel.
 *
 * Relationships:
 * - used only by the large-screen Klassrumskartan overview
 * - merges class-list and classroom management into one framed panel
 * - composes desktop-only rich sections for student and classroom previews
 * - leaves phone layout to PlannerPhoneOverviewSetupPanel
 */

import type { RoomTemplate, Roster } from "../classroomPlannerTypes";
import PlannerDesktopRosterOverviewSection from "./PlannerDesktopRosterOverviewSection.vue";
import PlannerDesktopTemplateOverviewSection from "./PlannerDesktopTemplateOverviewSection.vue";

defineProps<{
  selectedRoster: Roster | null;
  selectedRosterId: string | null;
  selectedRosterCountLabel?: string | null;
  availableRosters: Roster[];
  selectedTemplate: RoomTemplate | null;
  selectedTemplateId: string | null;
  availableTemplates: RoomTemplate[];
  isLoadingWorkspace: boolean;
  showRosterActions?: boolean;
  showTemplateActions?: boolean;
  rosterCreateDisabledReason?: string | null;
  rosterEditDisabledReason?: string | null;
  rosterDeleteDisabledReason?: string | null;
  templateCreateDisabledReason?: string | null;
  templateEditDisabledReason?: string | null;
  templateDeleteDisabledReason?: string | null;
}>();

const emit = defineEmits<{
  (e: "select-roster", rosterId: string): void;
  (e: "create-roster"): void;
  (e: "edit-roster"): void;
  (e: "delete-current-roster"): void;
  (e: "select-template", templateId: string | null): void;
  (e: "create-template"): void;
  (e: "edit-current-template", template?: RoomTemplate): void;
  (e: "delete-current-template"): void;
}>();
</script>

<template>
  <article
    class="planner-overview-setup-panel planner-overview-setup-panel-desktop planner-desktop-overview-setup-panel"
    data-test="overview-setup-panel"
  >
    <PlannerDesktopRosterOverviewSection
      :title="selectedRoster?.name ?? 'Klasslista'"
      :count-label="selectedRosterCountLabel"
      :selected-roster="selectedRoster"
      :selected-roster-id="selectedRosterId"
      :available-rosters="availableRosters"
      :is-loading-workspace="isLoadingWorkspace"
      :show-actions="showRosterActions"
      :create-disabled-reason="rosterCreateDisabledReason"
      :edit-disabled-reason="rosterEditDisabledReason"
      :delete-disabled-reason="rosterDeleteDisabledReason"
      @select-roster="emit('select-roster', $event)"
      @create-roster="emit('create-roster')"
      @edit-roster="emit('edit-roster')"
      @delete-current-roster="emit('delete-current-roster')"
    />

    <PlannerDesktopTemplateOverviewSection
      :selected-template="selectedTemplate"
      :selected-template-id="selectedTemplateId"
      :available-templates="availableTemplates"
      :is-loading-workspace="isLoadingWorkspace"
      :show-actions="showTemplateActions"
      :create-disabled-reason="templateCreateDisabledReason"
      :edit-disabled-reason="templateEditDisabledReason"
      :delete-disabled-reason="templateDeleteDisabledReason"
      @select-template="emit('select-template', $event)"
      @create-template="emit('create-template')"
      @edit-current-template="emit('edit-current-template', $event)"
      @delete-current-template="emit('delete-current-template')"
    />
  </article>
</template>
