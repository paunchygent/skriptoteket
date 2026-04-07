<script setup lang="ts">
/**
 * Classroom planner public guest workspace shell.
 *
 * This guest-only shell reuses the shared planner workspace surfaces for the
 * browser-owned public lane. It keeps `Regler`, Smart, and export parity with
 * the authenticated shell while intentionally hiding account-only history
 * affordances.
 */

import { computed, onUnmounted, ref, watch } from "vue";

import { useHelp } from "../../components/help/useHelp";
import { useToast } from "../../composables/useToast";
import type { RoomTemplate, Roster } from "./classroomPlannerTypes";
import PlannerGroupingSettingsDrawer from "./components/PlannerGroupingSettingsDrawer.vue";
import PlannerGroupingWorkspacePane from "./components/PlannerGroupingWorkspacePane.vue";
import PlannerGroupingWorkspaceToolbar from "./components/PlannerGroupingWorkspaceToolbar.vue";
import PlannerRulesWorkspacePane from "./components/PlannerRulesWorkspacePane.vue";
import PlannerSeatingSettingsDrawer from "./components/PlannerSeatingSettingsDrawer.vue";
import PlannerSeatingWorkspacePane from "./components/PlannerSeatingWorkspacePane.vue";
import PlannerSeatingWorkspaceToolbar from "./components/PlannerSeatingWorkspaceToolbar.vue";
import PlannerTopPanel from "./components/PlannerTopPanel.vue";
import PlannerWorkspaceModeSurface from "./components/PlannerWorkspaceModeSurface.vue";
import {
  resolveGuestWorkspaceTemplateContext,
  type GuestPlannerView,
} from "./classroomPlannerGuestTemplateContext";
import { PLANNER_WORKSPACE_SHELL_CLASS } from "./plannerWorkspaceLayout";
import { resolvePlannerWorkspaceDisabledReasons } from "./plannerWorkspacePrerequisites";
import { useClassroomState } from "./useClassroomState";
import { usePlannerUndoRedoShortcuts } from "./usePlannerUndoRedoShortcuts";
import type { GroupingExportOption, SeatingExportOption } from "./classroomPlannerExportApi";

const props = withDefaults(
  defineProps<{
    availableRosters?: Roster[];
    availableTemplates?: RoomTemplate[];
    selectedRosterId?: string | null;
    selectedTemplateId?: string | null;
    initialView?: GuestPlannerView;
    groupingExportBusy?: boolean;
    groupingExportStatusLabel?: string | null;
    groupingExportErrorMessage?: string | null;
    seatingExportBusy?: boolean;
    seatingExportStatusLabel?: string | null;
    seatingExportErrorMessage?: string | null;
  }>(),
  {
    availableRosters: () => [],
    availableTemplates: () => [],
    selectedRosterId: null,
    selectedTemplateId: null,
    initialView: "groups",
    groupingExportBusy: false,
    groupingExportStatusLabel: null,
    groupingExportErrorMessage: null,
    seatingExportBusy: false,
    seatingExportStatusLabel: null,
    seatingExportErrorMessage: null,
  },
);

const emit = defineEmits<{
  (e: "change-grouping-roster", payload: { rosterId: string }): void;
  (e: "change-grouping-template", payload: { templateId: string | null }): void;
  (e: "change-seating-template", payload: { templateId: string | null }): void;
  (e: "new-grouping-draft", payload: { templateId: string | null }): void;
  (e: "new-seating-draft", payload: { templateId: string }): void;
  (e: "edit-roster"): void;
  (e: "export-grouping-default"): void;
  (e: "export-grouping-option", option: GroupingExportOption): void;
  (e: "export-seating-default"): void;
  (e: "export-seating-option", option: SeatingExportOption): void;
  (e: "edit-current-template", template: RoomTemplate): void;
  (e: "select-workspace-mode", mode: "overview" | "grouping" | "seating" | "rules"): void;
  (e: "exit-app"): void;
}>();

const plannerState = useClassroomState();
const toast = useToast();

usePlannerUndoRedoShortcuts({
  plannerState,
});

function resolvePlannerView(requestedView: GuestPlannerView): GuestPlannerView {
  if (requestedView === "rules") {
    return "rules";
  }
  if (plannerState.draft?.draft_kind === "grouping") {
    return "groups";
  }
  if (plannerState.draft?.draft_kind === "seating") {
    return "seats";
  }
  return requestedView;
}

const currentView = ref<GuestPlannerView>(resolvePlannerView(props.initialView));
const selectedStudentId = ref<string | null>(null);
const isGroupingSettingsDrawerOpen = ref(false);
const isSeatingSettingsDrawerOpen = ref(false);
const pendingGroupingTemplateId = ref(plannerState.template?.id ?? props.selectedTemplateId ?? "");
const pendingSeatingTemplateId = ref(plannerState.template?.id ?? props.selectedTemplateId ?? "");
const lastGroupingSmartRunToast = ref<string | null>(null);
const lastSeatingSmartRunToast = ref<string | null>(null);

const liveTemplateId = computed(() => {
  return resolveGuestWorkspaceTemplateContext({
    currentView: currentView.value,
    selectedTemplateId: props.selectedTemplateId,
    plannerTemplateId: plannerState.template?.id ?? null,
  });
});
const selectedPlannerTemplate = computed(() => {
  const templateId = liveTemplateId.value;
  if (!templateId) {
    return null;
  }
  if (plannerState.template?.id === templateId) {
    return plannerState.template;
  }
  return props.availableTemplates.find((entry) => entry.id === templateId) ?? null;
});
const plannerTitle = computed(() => plannerState.roster?.name ?? "Planering");
const workspaceModeValue = computed<"overview" | "grouping" | "seating" | "rules">(() => {
  if (currentView.value === "groups") {
    return "grouping";
  }
  if (currentView.value === "rules") {
    return "rules";
  }
  return "seating";
});
const workspaceDisabledReasons = computed(() => {
  return resolvePlannerWorkspaceDisabledReasons({
    hasRoster: plannerState.roster !== null,
    hasTemplate: liveTemplateId.value !== null,
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
  if (currentView.value === "rules") {
    return "Här ställer du in regler som påverkar Smart i grupper och sittplatser.";
  }
  return "Dra elever till platserna och justera sittschemat direkt i klassrummet.";
});

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

function selectStudent(studentId: string): void {
  if (currentView.value === "rules") {
    if (plannerState.activeSeatingSmartTool) {
      plannerState.handleSeatingSmartToolStudentSelection(studentId);
    }
    selectedStudentId.value = null;
    return;
  }
  selectedStudentId.value = null;
}

async function reloadAfterConflict(): Promise<void> {
  await plannerState.reloadActiveWorkspace();
}

function selectWorkspaceMode(value: string): void {
  if (value === "overview" || value === "grouping" || value === "seating" || value === "rules") {
    emit("select-workspace-mode", value);
  }
}

function changeGroupingRoster(rosterId: string): void {
  emit("change-grouping-roster", { rosterId });
}

function changeGroupingTemplate(templateId: string | null): void {
  pendingGroupingTemplateId.value = templateId ?? "";
  emit("change-grouping-template", { templateId });
}

function changeSeatingTemplate(templateId: string | null): void {
  pendingSeatingTemplateId.value = templateId ?? "";
  emit("change-seating-template", { templateId });
}

function startNewGroupingDraft(): void {
  emit("new-grouping-draft", { templateId: plannerState.template?.id ?? null });
}

function openGroupingSettingsDrawer(): void {
  isGroupingSettingsDrawerOpen.value = true;
}

function closeGroupingSettingsDrawer(): void {
  isGroupingSettingsDrawerOpen.value = false;
}

function openSeatingSettingsDrawer(): void {
  isSeatingSettingsDrawerOpen.value = true;
}

function closeSeatingSettingsDrawer(): void {
  isSeatingSettingsDrawerOpen.value = false;
}

function openRules(): void {
  emit("select-workspace-mode", "rules");
}

function editCurrentTemplate(template: RoomTemplate): void {
  emit("edit-current-template", template);
}

function showSmartRunToast(options: {
  message: string | null;
  tone: "neutral" | "success" | "warning";
  lastToastRef: { value: string | null };
}): void {
  const { message, tone, lastToastRef } = options;
  if (!message) {
    lastToastRef.value = null;
    return;
  }

  const toastKey = `${tone}:${message}`;
  if (toastKey === lastToastRef.value) {
    return;
  }

  if (tone === "success") {
    toast.success(message);
  } else if (tone === "warning") {
    toast.warning(message);
  } else {
    toast.info(message);
  }
  lastToastRef.value = toastKey;
}

watch(
  () => props.initialView,
  (nextView) => {
    currentView.value = resolvePlannerView(nextView);
    isGroupingSettingsDrawerOpen.value = false;
    isSeatingSettingsDrawerOpen.value = false;
    selectedStudentId.value = null;
  },
);

watch(
  () => ({
    draftKind: plannerState.draft?.draft_kind ?? null,
    plannerTemplateId: plannerState.template?.id ?? null,
    selectedTemplateId: props.selectedTemplateId,
    currentView: currentView.value,
  }),
  () => {
    const nextView = resolvePlannerView(currentView.value);
    const nextTemplateId = resolveGuestWorkspaceTemplateContext({
      currentView: nextView,
      selectedTemplateId: props.selectedTemplateId,
      plannerTemplateId: plannerState.template?.id ?? null,
    }) ?? "";
    currentView.value = nextView;
    isGroupingSettingsDrawerOpen.value = false;
    isSeatingSettingsDrawerOpen.value = false;
    selectedStudentId.value = null;
    pendingGroupingTemplateId.value = nextTemplateId;
    pendingSeatingTemplateId.value = nextTemplateId;
  },
);

watch(
  () => ({
    message: plannerState.smartGroupingRunMessage,
    tone: plannerState.smartGroupingRunTone,
  }),
  ({ message, tone }) => {
    showSmartRunToast({
      message,
      tone,
      lastToastRef: lastGroupingSmartRunToast,
    });
  },
);

watch(
  () => ({
    message: plannerState.smartSeatingRunMessage,
    tone: plannerState.smartSeatingRunTone,
  }),
  ({ message, tone }) => {
    showSmartRunToast({
      message,
      tone,
      lastToastRef: lastSeatingSmartRunToast,
    });
  },
);
</script>

<template>
  <section :class="PLANNER_WORKSPACE_SHELL_CLASS">
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
        @click="void reloadAfterConflict()"
      >
        Ladda om utkast
      </button>
    </div>

    <PlannerTopPanel
      :title="plannerTitle"
      :context-label="contextLabel"
      :mode-value="workspaceModeValue"
      :show-rules-option="true"
      :grouping-disabled-reason="workspaceDisabledReasons.grouping"
      :seating-disabled-reason="workspaceDisabledReasons.seating"
      :rules-disabled-reason="workspaceDisabledReasons.rules"
      :supporting-text="supportingText"
      :status-label="plannerState.plannerStatusLabel"
      :status-message="plannerState.plannerStatusMessage"
      :status-tone="plannerState.plannerStatusTone"
      @update:mode-value="selectWorkspaceMode"
      @exit="emit('exit-app')"
    />

    <PlannerWorkspaceModeSurface
      v-if="currentView === 'groups'"
      view="groups"
    >
      <template #toolbar>
        <PlannerGroupingWorkspaceToolbar
          :available-rosters="availableRosters"
          :selected-roster-id="selectedRosterId"
          :smart-settings-open="isGroupingSettingsDrawerOpen"
          :export-busy="groupingExportBusy"
          :export-status-label="groupingExportStatusLabel"
          :export-error-message="groupingExportErrorMessage"
          :show-history-action="false"
          :show-smart-controls="true"
          :show-export-actions="true"
          @change-grouping-roster="changeGroupingRoster($event)"
          @new-grouping-draft="startNewGroupingDraft"
          @open-settings="openGroupingSettingsDrawer"
          @edit-roster="emit('edit-roster')"
          @export-default="emit('export-grouping-default')"
          @export-option="emit('export-grouping-option', $event)"
        />
      </template>

      <PlannerGroupingWorkspacePane />
    </PlannerWorkspaceModeSurface>

    <PlannerWorkspaceModeSurface
      v-else-if="currentView === 'seats'"
      view="seats"
    >
      <template #toolbar>
        <PlannerSeatingWorkspaceToolbar
          :available-templates="availableTemplates"
          :selected-template-id="pendingSeatingTemplateId || null"
          :smart-settings-open="isSeatingSettingsDrawerOpen"
          :export-busy="seatingExportBusy"
          :export-status-label="seatingExportStatusLabel"
          :export-error-message="seatingExportErrorMessage"
          :show-history-action="false"
          :show-smart-controls="true"
          :show-export-actions="true"
          @change-seating-template="changeSeatingTemplate($event)"
          @new-seating-draft="emit('new-seating-draft', { templateId: $event })"
          @edit-roster="emit('edit-roster')"
          @edit-current-template="editCurrentTemplate"
          @open-settings="openSeatingSettingsDrawer"
          @export-default="emit('export-seating-default')"
          @export-option="emit('export-seating-option', $event)"
        />
      </template>

      <PlannerSeatingWorkspacePane
        :selected-template-id="pendingSeatingTemplateId || null"
      />
    </PlannerWorkspaceModeSurface>

    <PlannerRulesWorkspacePane
      v-else
      :selected-student-id="selectedStudentId"
      @student-selected="selectStudent"
    />

    <PlannerGroupingSettingsDrawer
      :open="currentView === 'groups' && isGroupingSettingsDrawerOpen"
      :available-templates="availableTemplates"
      :selected-template-id="pendingGroupingTemplateId || null"
      :show-history-setting="false"
      @close="closeGroupingSettingsDrawer"
      @change-grouping-template="changeGroupingTemplate($event)"
      @open-rules="openRules"
    />

    <PlannerSeatingSettingsDrawer
      :open="currentView === 'seats' && isSeatingSettingsDrawerOpen"
      :show-history-setting="false"
      @close="closeSeatingSettingsDrawer"
      @open-rules="openRules"
    />
  </section>
</template>
