<script setup lang="ts">
/**
 * Planner workspace shell.
 *
 * This component renders the active classroom-planning workspace after a draft
 * has been created or resumed. It keeps the default surface focused on one
 * teacher task at a time so grouping and seating do not teach a shared
 * whole-workspace mental model.
 */

import { computed, ref, watch } from "vue";

import type { ClassWorkspaceSummary, RoomTemplate } from "../classroomPlannerTypes";
import PlannerGroupingWorkspacePane from "./PlannerGroupingWorkspacePane.vue";
import PlannerHistoryDrawer from "./PlannerHistoryDrawer.vue";
import PlannerMetadataDrawer from "./PlannerMetadataDrawer.vue";
import PlannerSeatingWorkspacePane from "./PlannerSeatingWorkspacePane.vue";
import PlannerTopPanel from "./PlannerTopPanel.vue";
import { useClassroomState } from "../useClassroomState";

type PlannerView = "groups" | "seats";

const props = withDefaults(
  defineProps<{
    availableTemplates?: RoomTemplate[];
    initialView?: PlannerView;
    workspaceSummary?: ClassWorkspaceSummary | null;
    seatingLifecycleBusy?: boolean;
    seatingHistoryBusyDraftId?: string | null;
  }>(),
  {
    availableTemplates: () => [],
    initialView: "groups",
    workspaceSummary: null,
    seatingLifecycleBusy: false,
    seatingHistoryBusyDraftId: null,
  },
);

const emit = defineEmits<{
  (e: "change-grouping-template", payload: { templateId: string | null }): void;
  (e: "change-seating-template", payload: { templateId: string | null }): void;
  (e: "new-grouping-draft", payload: { templateId: string | null }): void;
  (e: "new-seating-draft", payload: { templateId: string }): void;
  (e: "edit-roster"): void;
  (e: "open-grouping-history-draft", draftId: string): void;
  (e: "delete-grouping-history-draft", draftId: string): void;
  (e: "open-seating-history-draft", draftId: string): void;
  (e: "delete-seating-history-draft", draftId: string): void;
  (e: "edit-current-template", template: RoomTemplate): void;
  (e: "select-workspace-mode", mode: "overview" | "grouping" | "seating"): void;
  (e: "exit-app"): void;
}>();

const plannerState = useClassroomState();

function resolvePlannerView(requestedView: PlannerView): PlannerView {
  if (plannerState.draft?.draft_kind === "grouping") {
    return "groups";
  }
  if (plannerState.draft?.draft_kind === "seating") {
    return "seats";
  }
  return requestedView;
}

const currentView = ref<PlannerView>(resolvePlannerView(props.initialView));
const selectedStudentId = ref<string | null>(null);
const isMetadataDrawerOpen = ref(false);
const openHistoryDrawerKind = ref<"grouping" | "seating" | null>(null);
const pendingGroupingTemplateId = ref(plannerState.template?.id ?? "");
const pendingSeatingTemplateId = ref(plannerState.template?.id ?? "");
const plannerTitle = computed(() => plannerState.roster?.name ?? "Klassarbetsyta");
const workspaceModeValue = computed<"overview" | "grouping" | "seating">(() => {
  return currentView.value === "groups" ? "grouping" : "seating";
});
const isSeatWorkspaceWithoutTemplate = computed(() => {
  return currentView.value === "seats" && plannerState.template === null;
});
const workspaceContextLabel = computed(() => plannerState.template?.name ?? "Utan klassrum");
const saveStatusLabel = computed(() => {
  switch (plannerState.saveStatus) {
    case "saving":
      return "Sparar";
    case "saved":
      return "Sparad";
    case "error":
      return "Inte sparad";
    case "conflict":
      return "Konflikt";
    default:
      return "Ingen ändring";
  }
});
const saveStatusTone = computed<"neutral" | "success" | "warning" | "danger">(() => {
  switch (plannerState.saveStatus) {
    case "saved":
      return "success";
    case "saving":
      return "warning";
    case "error":
    case "conflict":
      return "danger";
    default:
      return "neutral";
  }
});
const hasSaveMessage = computed(() => {
  return typeof plannerState.saveMessage === "string" && plannerState.saveMessage.length > 0;
});
const activeGroupingSummary = computed(() => props.workspaceSummary?.active_grouping_draft ?? null);
const groupingHistorySummaries = computed(() => props.workspaceSummary?.grouping_history ?? []);
const activeSeatingSummary = computed(() => props.workspaceSummary?.active_seating_draft ?? null);
const seatingHistorySummaries = computed(() => props.workspaceSummary?.seating_history ?? []);
const isHistoryDrawerOpen = computed(() => openHistoryDrawerKind.value !== null);
const historyDrawerTitle = computed(() => {
  return openHistoryDrawerKind.value === "seating" ? "Sittplatser" : "Grupper";
});
const historyDrawerActiveSummary = computed(() => {
  return openHistoryDrawerKind.value === "seating"
    ? activeSeatingSummary.value
    : activeGroupingSummary.value;
});
const historyDrawerSummaries = computed(() => {
  return openHistoryDrawerKind.value === "seating"
    ? seatingHistorySummaries.value
    : groupingHistorySummaries.value;
});
const historyDrawerEmptyLabel = computed(() => {
  return openHistoryDrawerKind.value === "seating"
    ? "Ingen sitthistorik ännu."
    : "Ingen grupphistorik ännu.";
});
const historyDrawerActiveLabel = computed(() => {
  return openHistoryDrawerKind.value === "seating"
    ? "Aktuellt sittschema"
    : "Aktuellt grupputkast";
});
const historyDrawerLabel = computed(() => {
  return openHistoryDrawerKind.value === "seating"
    ? "Tidigare sittscheman"
    : "Tidigare grupputkast";
});
const currentViewHint = computed(() => {
  if (isSeatWorkspaceWithoutTemplate.value) {
    return "Välj eller byt klassrum direkt här i sittschemat.";
  }
  if (currentView.value === "groups") {
    return "Dra elever mellan grupperna tills grupparbetet sitter.";
  }
  return "Dra elever till platserna och öppna elevanteckningar vid behov.";
});

function selectStudent(studentId: string): void {
  selectedStudentId.value = studentId;
  if (currentView.value !== "seats") {
    isMetadataDrawerOpen.value = false;
    return;
  }
  isMetadataDrawerOpen.value = true;
}

async function reloadAfterConflict(): Promise<void> {
  await plannerState.reloadActiveWorkspace();
}

function changeSeatingTemplate(templateId: string | null): void {
  pendingSeatingTemplateId.value = templateId ?? "";
  emit("change-seating-template", { templateId });
}

function changeGroupingTemplate(templateId: string | null): void {
  pendingGroupingTemplateId.value = templateId ?? "";
  emit("change-grouping-template", { templateId });
}

function startNewGroupingDraft(): void {
  emit("new-grouping-draft", { templateId: plannerState.template?.id ?? null });
}

function openGroupingHistoryDrawer(): void {
  openHistoryDrawerKind.value = "grouping";
}

function openSeatingHistoryDrawer(): void {
  if (props.seatingLifecycleBusy) {
    return;
  }
  openHistoryDrawerKind.value = "seating";
}

function closeHistoryDrawer(): void {
  openHistoryDrawerKind.value = null;
}

function openGroupingHistoryDraft(draftId: string): void {
  closeHistoryDrawer();
  emit("open-grouping-history-draft", draftId);
}

function deleteGroupingHistoryDraft(draftId: string): void {
  closeHistoryDrawer();
  emit("delete-grouping-history-draft", draftId);
}

function openSeatingHistoryDraft(draftId: string): void {
  if (props.seatingLifecycleBusy) {
    return;
  }
  closeHistoryDrawer();
  emit("open-seating-history-draft", draftId);
}

function deleteSeatingHistoryDraft(draftId: string): void {
  if (props.seatingLifecycleBusy) {
    return;
  }
  closeHistoryDrawer();
  emit("delete-seating-history-draft", draftId);
}

function editCurrentTemplate(template: RoomTemplate): void {
  emit("edit-current-template", template);
}

function selectWorkspaceMode(value: string): void {
  if (value === "overview" || value === "grouping" || value === "seating") {
    emit("select-workspace-mode", value);
  }
}

watch(
  () => props.initialView,
  (nextView) => {
    currentView.value = resolvePlannerView(nextView);
    openHistoryDrawerKind.value = null;
    isMetadataDrawerOpen.value = false;
    selectedStudentId.value = null;
  },
);

watch(
  () => [plannerState.draft?.draft_kind ?? null, plannerState.template?.id ?? null] as const,
  () => {
    currentView.value = resolvePlannerView(currentView.value);
    openHistoryDrawerKind.value = null;
    isMetadataDrawerOpen.value = false;
    selectedStudentId.value = null;
    pendingGroupingTemplateId.value = plannerState.template?.id ?? "";
    pendingSeatingTemplateId.value = plannerState.template?.id ?? "";
  },
);

</script>

<template>
  <section class="space-y-6">
    <div
      v-if="plannerState.saveStatus === 'conflict'"
      class="system-message system-message-warning"
    >
      <div class="system-message-content">
        {{ plannerState.saveMessage }}
      </div>
      <button
        type="button"
        class="btn-ghost border-navy/30 bg-white shadow-none"
        @click="reloadAfterConflict"
      >
        Ladda om utkast
      </button>
    </div>

    <PlannerTopPanel
      :title="plannerTitle"
      :context-label="isSeatWorkspaceWithoutTemplate ? 'Välj klassrum i sittschemat' : `${workspaceContextLabel} · version ${plannerState.draft?.revision ?? 0}`"
      :mode-value="workspaceModeValue"
      :supporting-text="currentViewHint"
      :status-label="saveStatusLabel"
      :status-message="hasSaveMessage ? plannerState.saveMessage : null"
      :status-tone="saveStatusTone"
      @update:mode-value="selectWorkspaceMode"
      @exit="emit('exit-app')"
    />

    <PlannerGroupingWorkspacePane
      v-if="currentView === 'groups'"
      :selected-student-id="selectedStudentId"
      :available-templates="availableTemplates"
      :selected-template-id="pendingGroupingTemplateId"
      @new-grouping-draft="startNewGroupingDraft"
      @open-history="openGroupingHistoryDrawer"
      @edit-roster="emit('edit-roster')"
      @student-selected="selectStudent"
      @change-grouping-template="changeGroupingTemplate"
    />
    <PlannerSeatingWorkspacePane
      v-if="currentView === 'seats'"
      :selected-student-id="selectedStudentId"
      :available-templates="availableTemplates"
      :selected-template-id="pendingSeatingTemplateId"
      :seating-lifecycle-busy="seatingLifecycleBusy"
      @student-selected="selectStudent"
      @change-seating-template="changeSeatingTemplate"
      @new-seating-draft="emit('new-seating-draft', { templateId: $event })"
      @edit-current-template="editCurrentTemplate"
      @open-history="openSeatingHistoryDrawer"
    />

    <PlannerMetadataDrawer
      :selected-student-id="selectedStudentId"
      :open="isMetadataDrawerOpen"
      @close="isMetadataDrawerOpen = false"
    />

    <PlannerHistoryDrawer
      :open="isHistoryDrawerOpen"
      :title="historyDrawerTitle"
      :active-summary="historyDrawerActiveSummary"
      :summaries="historyDrawerSummaries"
      :empty-label="historyDrawerEmptyLabel"
      :active-label="historyDrawerActiveLabel"
      :history-label="historyDrawerLabel"
      :can-open-summaries="!(openHistoryDrawerKind === 'seating' && props.seatingLifecycleBusy)"
      :can-delete-summaries="!(openHistoryDrawerKind === 'seating' && props.seatingLifecycleBusy)"
      :busy-summary-id="openHistoryDrawerKind === 'seating' ? props.seatingHistoryBusyDraftId : null"
      @close="closeHistoryDrawer"
      @open-summary="
        openHistoryDrawerKind === 'seating'
          ? openSeatingHistoryDraft($event)
          : openGroupingHistoryDraft($event)
      "
      @delete-summary="
        openHistoryDrawerKind === 'seating'
          ? deleteSeatingHistoryDraft($event)
          : deleteGroupingHistoryDraft($event)
      "
    />
  </section>
</template>
