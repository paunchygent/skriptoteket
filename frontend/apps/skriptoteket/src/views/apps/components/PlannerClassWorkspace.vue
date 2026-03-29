<script setup lang="ts">
/**
 * Class-first planner workspace.
 *
 * This component is now the only home surface for Klassrumskartan. It keeps
 * overview as the default entry state, folds the no-class empty state into the
 * same surface, relies on the segmented toggle as the only way to enter
 * task work, and composes overview-specific subcomponents instead of mixing
 * resumable cards, roster controls, and classroom controls in one file.
 */

import { computed, onUnmounted, ref } from "vue";

import type {
  ClassWorkspaceSummary,
  PlanDraftSummary,
  RoomTemplate,
  Roster,
} from "../classroomPlannerTypes";
import { useHelp } from "../../../components/help/useHelp";
import PlannerRosterOverviewPanel from "./PlannerRosterOverviewPanel.vue";
import PlannerTemplateOverviewPanel from "./PlannerTemplateOverviewPanel.vue";
import PlannerTopPanel from "./PlannerTopPanel.vue";

const CLASS_PREVIEW_NAME_LIMIT = 33;

const props = defineProps<{
  workspaceSummary: ClassWorkspaceSummary | null;
  availableRosters: Roster[];
  availableTemplates: RoomTemplate[];
  selectedRosterId: string | null;
  selectedTemplateId: string | null;
  isLoadingWorkspace: boolean;
  transitionLabel?: string | null;
  visibleGroupingDraft: PlanDraftSummary | null;
  visibleSeatingDraft: PlanDraftSummary | null;
}>();

const emit = defineEmits<{
  (e: "exit-app"): void;
  (e: "create-roster"): void;
  (e: "edit-roster"): void;
  (e: "delete-current-roster"): void;
  (e: "select-roster", rosterId: string): void;
  (e: "create-template"): void;
  (e: "select-template", templateId: string | null): void;
  (e: "edit-current-template", template?: RoomTemplate): void;
  (e: "delete-current-template"): void;
  (e: "open-grouping", payload: { templateId: string | null }): void;
  (e: "open-seating", payload: { templateId: string | null }): void;
  (e: "open-rules"): void;
  (e: "dismiss-grouping-draft"): void;
  (e: "dismiss-seating-draft"): void;
}>();

const workspaceMode = ref<"overview" | "grouping" | "seating" | "rules">("overview");

// Keep the global help panel aware that we are in overview mode.
const { setHelpContext, clearHelpContext } = useHelp();
setHelpContext("planner_overview");
onUnmounted(() => clearHelpContext("planner_overview"));

const activeRosterSummary = computed(() => props.workspaceSummary?.roster ?? null);
const selectedRoster = computed(() => {
  return props.availableRosters.find((roster) => roster.id === props.selectedRosterId) ?? null;
});
const selectedTemplate = computed(() => {
  return props.availableTemplates.find((template) => template.id === props.selectedTemplateId) ?? null;
});
const selectedRosterPreviewNames = computed(() => {
  const roster = selectedRoster.value;
  if (!roster) {
    return [];
  }

  const sortedNames = [...roster.students]
    .map((student) => student.display_name.trim())
    .filter((displayName) => displayName.length > 0)
    .sort((left, right) => {
      const leftFirstName = left.split(/\s+/)[0] ?? left;
      const rightFirstName = right.split(/\s+/)[0] ?? right;
      const firstNameComparison = leftFirstName.localeCompare(rightFirstName, "sv");
      if (firstNameComparison !== 0) {
        return firstNameComparison;
      }
      return left.localeCompare(right, "sv");
    });

  if (sortedNames.length <= CLASS_PREVIEW_NAME_LIMIT) {
    return sortedNames;
  }

  return [...sortedNames.slice(0, CLASS_PREVIEW_NAME_LIMIT), "..."];
});
const workspaceContextLabel = computed(() => {
  if (!selectedTemplate.value) {
    return "Inget klassrum valt";
  }
  return `Klassrum: ${selectedTemplate.value.name}`;
});
const workspaceHomeTitle = computed(() => {
  return selectedRoster.value?.name ?? activeRosterSummary.value?.name ?? "Planering";
});
const selectedRosterCountLabel = computed(() => {
  if (activeRosterSummary.value) {
    return `${activeRosterSummary.value.student_count} elever`;
  }
  if (selectedRoster.value) {
    return `${selectedRoster.value.students.length} elever`;
  }
  return "Välj en klasslista";
});

function selectWorkspaceMode(value: string): void {
  if (value === "overview") {
    workspaceMode.value = value;
    return;
  }

  if (value === "grouping") {
    emit("open-grouping", { templateId: null });
    return;
  }

  if (value === "seating") {
    emit("open-seating", { templateId: props.selectedTemplateId });
    return;
  }

  if (value === "rules") {
    emit("open-rules");
  }
}

</script>

<template>
  <section class="space-y-4">
    <PlannerTopPanel
      :title="workspaceHomeTitle"
      :context-label="workspaceContextLabel"
      :mode-value="workspaceMode"
      status-tone="neutral"
      @update:mode-value="selectWorkspaceMode"
      @exit="emit('exit-app')"
    />

    <div
      v-if="transitionLabel || isLoadingWorkspace"
      class="border border-navy bg-white px-4 py-12 text-center text-sm font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy shadow-brutal-sm"
    >
      {{ transitionLabel ?? "Laddar planeringen..." }}
    </div>

    <div
      v-else
      class="grid gap-3 xl:grid-cols-2"
    >
      <PlannerRosterOverviewPanel
        :title="selectedRoster?.name ?? activeRosterSummary?.name ?? 'Ingen klass vald'"
        :count-label="selectedRosterCountLabel"
        :selected-roster="selectedRoster"
        :selected-roster-id="selectedRosterId"
        :available-rosters="availableRosters"
        :selected-roster-preview-names="selectedRosterPreviewNames"
        :is-loading-workspace="isLoadingWorkspace"
        @select-roster="emit('select-roster', $event)"
        @create-roster="emit('create-roster')"
        @edit-roster="emit('edit-roster')"
        @delete-current-roster="emit('delete-current-roster')"
      />

      <PlannerTemplateOverviewPanel
        :selected-template="selectedTemplate"
        :selected-template-id="selectedTemplateId"
        :available-templates="availableTemplates"
        :is-loading-workspace="isLoadingWorkspace"
        @select-template="emit('select-template', $event)"
        @create-template="emit('create-template')"
        @edit-current-template="emit('edit-current-template', $event)"
        @delete-current-template="emit('delete-current-template')"
      />
    </div>
  </section>
</template>
