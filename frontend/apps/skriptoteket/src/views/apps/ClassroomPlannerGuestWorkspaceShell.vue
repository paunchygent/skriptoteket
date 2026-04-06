<script setup lang="ts">
/**
 * Classroom planner public guest workspace shell.
 *
 * This guest-only shell keeps checkpoint-3 honest by exposing only the
 * browser-owned grouping and seating lanes. It reuses the shared planner
 * panes and toolbars, while intentionally omitting authenticated-only rules,
 * history, export, and recovery affordances.
 */

import { computed, onUnmounted, watch } from "vue";

import { useHelp } from "../../components/help/useHelp";
import type { RoomTemplate, Roster } from "./classroomPlannerTypes";
import PlannerGroupingWorkspacePane from "./components/PlannerGroupingWorkspacePane.vue";
import PlannerGroupingWorkspaceToolbar from "./components/PlannerGroupingWorkspaceToolbar.vue";
import PlannerSeatingWorkspacePane from "./components/PlannerSeatingWorkspacePane.vue";
import PlannerSeatingWorkspaceToolbar from "./components/PlannerSeatingWorkspaceToolbar.vue";
import PlannerTopPanel from "./components/PlannerTopPanel.vue";
import { resolvePlannerWorkspaceDisabledReasons } from "./plannerWorkspacePrerequisites";
import { useClassroomState } from "./useClassroomState";

type GuestPlannerView = "groups" | "seats";

const props = withDefaults(
  defineProps<{
    availableRosters?: Roster[];
    availableTemplates?: RoomTemplate[];
    selectedRosterId?: string | null;
    selectedTemplateId?: string | null;
    initialView?: GuestPlannerView;
  }>(),
  {
    availableRosters: () => [],
    availableTemplates: () => [],
    selectedRosterId: null,
    selectedTemplateId: null,
    initialView: "groups",
  },
);

const emit = defineEmits<{
  (e: "change-grouping-roster", payload: { rosterId: string }): void;
  (e: "change-seating-template", payload: { templateId: string | null }): void;
  (e: "new-grouping-draft", payload: { templateId: string | null }): void;
  (e: "new-seating-draft", payload: { templateId: string }): void;
  (e: "edit-roster"): void;
  (e: "edit-current-template", template: RoomTemplate): void;
  (e: "select-workspace-mode", mode: "overview" | "grouping" | "seating"): void;
  (e: "exit-app"): void;
}>();

const plannerState = useClassroomState();

function resolvePlannerView(requestedView: GuestPlannerView): GuestPlannerView {
  if (plannerState.draft?.draft_kind === "seating") {
    return "seats";
  }
  return requestedView;
}

const currentView = computed<GuestPlannerView>(() => resolvePlannerView(props.initialView));
const selectedPlannerTemplate = computed(() => {
  if (plannerState.template) {
    return plannerState.template;
  }
  return props.availableTemplates.find((entry) => entry.id === props.selectedTemplateId) ?? null;
});
const plannerTitle = computed(() => plannerState.roster?.name ?? "Planering");
const workspaceModeValue = computed<"overview" | "grouping" | "seating">(() => {
  return currentView.value === "groups" ? "grouping" : "seating";
});
const workspaceDisabledReasons = computed(() => {
  return resolvePlannerWorkspaceDisabledReasons({
    hasRoster: plannerState.roster !== null,
    hasTemplate: selectedPlannerTemplate.value !== null,
  });
});
const isSeatWorkspaceWithoutTemplate = computed(() => {
  return currentView.value === "seats" && selectedPlannerTemplate.value === null;
});
const contextLabel = computed(() => {
  if (isSeatWorkspaceWithoutTemplate.value) {
    return "Välj klassrum i sittschemat";
  }
  return selectedPlannerTemplate.value?.name ?? "Utan klassrum";
});
const supportingText = computed(() => {
  if (isSeatWorkspaceWithoutTemplate.value) {
    return "Välj eller byt klassrum direkt här i sittschemat.";
  }
  if (currentView.value === "groups") {
    return "Slumpa eller placera eleverna och dra dem mellan grupperna tills du är nöjd.";
  }
  return "Dra elever till platserna och justera sittschemat direkt i klassrummet.";
});

function reloadAfterConflict(): void {
  void plannerState.reloadActiveWorkspace();
}

function selectWorkspaceMode(value: string): void {
  if (value === "overview" || value === "grouping" || value === "seating") {
    emit("select-workspace-mode", value);
  }
}

function changeGroupingRoster(rosterId: string): void {
  emit("change-grouping-roster", { rosterId });
}

function changeSeatingTemplate(templateId: string | null): void {
  emit("change-seating-template", { templateId });
}

function startNewGroupingDraft(): void {
  emit("new-grouping-draft", { templateId: plannerState.template?.id ?? null });
}

function editCurrentTemplate(template: RoomTemplate): void {
  emit("edit-current-template", template);
}

const { setHelpContext, clearHelpContext } = useHelp();
watch(
  workspaceModeValue,
  (mode, previousMode) => {
    if (previousMode) {
      clearHelpContext(`planner_${previousMode}`);
    }
    setHelpContext(`planner_${mode}`);
  },
  { immediate: true },
);
onUnmounted(() => clearHelpContext(`planner_${workspaceModeValue.value}`));
</script>

<template>
  <section class="space-y-4 xl:flex xl:min-h-0 xl:flex-col">
    <div
      v-if="plannerState.plannerConflictMessage"
      class="system-message system-message-warning"
    >
      <div class="system-message-content">
        {{ plannerState.plannerConflictMessage }}
      </div>
      <button
        type="button"
        class="btn-ghost planner-btn-ghost"
        @click="reloadAfterConflict"
      >
        Ladda om utkast
      </button>
    </div>

    <PlannerTopPanel
      :title="plannerTitle"
      :context-label="contextLabel"
      :mode-value="workspaceModeValue"
      :show-rules-option="false"
      :grouping-disabled-reason="workspaceDisabledReasons.grouping"
      :seating-disabled-reason="workspaceDisabledReasons.seating"
      :supporting-text="supportingText"
      :status-label="plannerState.plannerStatusLabel"
      :status-message="plannerState.plannerStatusMessage"
      :status-tone="plannerState.plannerStatusTone"
      @update:mode-value="selectWorkspaceMode"
      @exit="emit('exit-app')"
    />

    <div
      v-if="currentView === 'groups'"
      class="flex flex-col gap-4 xl:min-h-0 xl:flex-1"
    >
      <div
        class="sticky top-0 z-20 md:-top-4"
        data-ui="planner-workspace-toolbar-shell"
        data-view="groups"
      >
        <PlannerGroupingWorkspaceToolbar
          :available-rosters="availableRosters"
          :selected-roster-id="selectedRosterId"
          :show-history-action="false"
          :show-smart-controls="false"
          :show-export-actions="false"
          @change-grouping-roster="changeGroupingRoster($event)"
          @new-grouping-draft="startNewGroupingDraft"
          @edit-roster="emit('edit-roster')"
        />
      </div>

      <div
        class="xl:min-h-0 xl:max-h-full xl:overflow-y-auto"
        data-ui="planner-workspace-pane-shell"
        data-view="groups"
      >
        <PlannerGroupingWorkspacePane />
      </div>
    </div>

    <div
      v-else
      class="flex flex-col gap-4 xl:min-h-0 xl:flex-1"
    >
      <div
        class="sticky top-0 z-20 md:-top-4"
        data-ui="planner-workspace-toolbar-shell"
        data-view="seats"
      >
        <PlannerSeatingWorkspaceToolbar
          :available-templates="availableTemplates"
          :selected-template-id="selectedPlannerTemplate?.id ?? null"
          :show-history-action="false"
          :show-smart-controls="false"
          :show-export-actions="false"
          @change-seating-template="changeSeatingTemplate($event)"
          @new-seating-draft="emit('new-seating-draft', { templateId: $event })"
          @edit-roster="emit('edit-roster')"
          @edit-current-template="editCurrentTemplate"
        />
      </div>

      <div
        class="xl:min-h-0 xl:max-h-full xl:overflow-y-auto"
        data-ui="planner-workspace-pane-shell"
        data-view="seats"
      >
        <PlannerSeatingWorkspacePane
          :selected-template-id="selectedPlannerTemplate?.id ?? null"
        />
      </div>
    </div>
  </section>
</template>
