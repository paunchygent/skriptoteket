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
import PlannerRulesWorkspacePane from "./PlannerRulesWorkspacePane.vue";
import PlannerSeatingWorkspacePane from "./PlannerSeatingWorkspacePane.vue";
import PlannerTopPanel from "./PlannerTopPanel.vue";
import type { GroupingExportOption, SeatingExportOption } from "../classroomPlannerExportApi";
import { useClassroomState } from "../useClassroomState";

type PlannerView = "groups" | "seats" | "rules";

const props = withDefaults(
  defineProps<{
    availableTemplates?: RoomTemplate[];
    initialView?: PlannerView;
    workspaceSummary?: ClassWorkspaceSummary | null;
    seatingLifecycleBusy?: boolean;
    seatingHistoryBusyDraftId?: string | null;
    groupingExportBusy?: boolean;
    groupingExportStatusLabel?: string | null;
    groupingExportErrorMessage?: string | null;
    canDownloadLatestGroupingExport?: boolean;
    seatingExportBusy?: boolean;
    seatingExportStatusLabel?: string | null;
    seatingExportErrorMessage?: string | null;
    canDownloadLatestSeatingExport?: boolean;
    transitionLabel?: string | null;
    workspaceNotice?: string | null;
  }>(),
  {
    availableTemplates: () => [],
    initialView: "groups",
    workspaceSummary: null,
    seatingLifecycleBusy: false,
    seatingHistoryBusyDraftId: null,
    groupingExportBusy: false,
    groupingExportStatusLabel: null,
    groupingExportErrorMessage: null,
    canDownloadLatestGroupingExport: false,
    seatingExportBusy: false,
    seatingExportStatusLabel: null,
    seatingExportErrorMessage: null,
    canDownloadLatestSeatingExport: false,
    transitionLabel: null,
    workspaceNotice: null,
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
  (e: "export-grouping-default"): void;
  (e: "export-grouping-option", option: GroupingExportOption): void;
  (e: "download-latest-grouping-export"): void;
  (e: "export-seating-default"): void;
  (e: "export-seating-option", option: SeatingExportOption): void;
  (e: "download-latest-seating-export"): void;
  (e: "edit-current-template", template: RoomTemplate): void;
  (e: "open-rules"): void;
  (e: "select-workspace-mode", mode: "overview" | "grouping" | "seating" | "rules"): void;
  (e: "dismiss-workspace-notice"): void;
  (e: "exit-app"): void;
}>();

const plannerState = useClassroomState();

function resolvePlannerView(requestedView: PlannerView): PlannerView {
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

const currentView = ref<PlannerView>(resolvePlannerView(props.initialView));
const selectedStudentId = ref<string | null>(null);
const isMetadataDrawerOpen = ref(false);
const openHistoryDrawerKind = ref<"grouping" | "seating" | null>(null);
const pendingGroupingTemplateId = ref(plannerState.template?.id ?? "");
const pendingSeatingTemplateId = ref(plannerState.template?.id ?? "");
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
const isSeatWorkspaceWithoutTemplate = computed(() => {
  return currentView.value === "seats" && plannerState.template === null;
});
const workspaceContextLabel = computed(() => plannerState.template?.name ?? "Utan klassrum");
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
  if (currentView.value === "rules") {
    return "Arbeta med regler i planeringskartan och växla till sittschema när det finns ett aktuellt upplägg.";
  }
  return "Dra elever till platserna och justera sittschemat direkt i klassrummet.";
});

function selectStudent(studentId: string): void {
  if (
    currentView.value === "rules"
    && plannerState.activeSeatingSmartTool
    && plannerState.handleSeatingSmartToolStudentSelection(studentId)
  ) {
    selectedStudentId.value = null;
    isMetadataDrawerOpen.value = false;
    return;
  }

  selectedStudentId.value = studentId;
  isMetadataDrawerOpen.value = currentView.value === "seats";
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
  if (value === "overview" || value === "grouping" || value === "seating" || value === "rules") {
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

    <div
      v-if="transitionLabel"
      class="border border-navy bg-white px-4 py-3 text-sm font-semibold text-navy shadow-brutal-sm"
      data-test="planner-workspace-transition"
    >
      {{ transitionLabel }}
    </div>

    <div
      v-if="workspaceNotice"
      class="system-message system-message-info"
      data-test="planner-workspace-notice"
    >
      <div class="system-message-content">
        {{ workspaceNotice }}
      </div>
      <button
        type="button"
        class="btn-ghost planner-btn-ghost"
        @click="emit('dismiss-workspace-notice')"
      >
        Stäng
      </button>
    </div>

    <PlannerTopPanel
      :title="plannerTitle"
      :context-label="isSeatWorkspaceWithoutTemplate ? 'Välj klassrum i sittschemat' : workspaceContextLabel"
      :mode-value="workspaceModeValue"
      :supporting-text="currentViewHint"
      :status-label="plannerState.plannerStatusLabel"
      :status-message="plannerState.plannerStatusMessage"
      :status-tone="plannerState.plannerStatusTone"
      @update:mode-value="selectWorkspaceMode"
      @exit="emit('exit-app')"
    />

    <PlannerRulesWorkspacePane
      v-if="currentView === 'rules'"
      :selected-student-id="selectedStudentId"
      @student-selected="selectStudent"
    />

    <PlannerGroupingWorkspacePane
      v-if="currentView === 'groups'"
      :selected-student-id="selectedStudentId"
      :available-templates="availableTemplates"
      :selected-template-id="pendingGroupingTemplateId"
      :export-busy="groupingExportBusy"
      :export-status-label="groupingExportStatusLabel"
      :export-error-message="groupingExportErrorMessage"
      :can-download-latest-export="canDownloadLatestGroupingExport"
      @new-grouping-draft="startNewGroupingDraft"
      @open-history="openGroupingHistoryDrawer"
      @open-rules="emit('open-rules')"
      @edit-roster="emit('edit-roster')"
      @student-selected="selectStudent"
      @change-grouping-template="changeGroupingTemplate"
      @export-default="emit('export-grouping-default')"
      @export-option="emit('export-grouping-option', $event)"
      @download-latest-export="emit('download-latest-grouping-export')"
    />
    <PlannerSeatingWorkspacePane
      v-if="currentView === 'seats'"
      :selected-student-id="selectedStudentId"
      :available-templates="availableTemplates"
      :selected-template-id="pendingSeatingTemplateId"
      :seating-lifecycle-busy="seatingLifecycleBusy"
      :export-busy="seatingExportBusy"
      :export-status-label="seatingExportStatusLabel"
      :export-error-message="seatingExportErrorMessage"
      :can-download-latest-export="canDownloadLatestSeatingExport"
      @student-selected="selectStudent"
      @change-seating-template="changeSeatingTemplate"
      @new-seating-draft="emit('new-seating-draft', { templateId: $event })"
      @export-default="emit('export-seating-default')"
      @export-option="emit('export-seating-option', $event)"
      @download-latest-export="emit('download-latest-seating-export')"
      @edit-current-template="editCurrentTemplate"
      @open-rules="emit('open-rules')"
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
