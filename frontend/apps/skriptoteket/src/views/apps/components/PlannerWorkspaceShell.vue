<script setup lang="ts">
/**
 * Planner workspace shell.
 *
 * This component renders the active classroom-planning workspace after a draft
 * has been created or resumed. It keeps the default surface focused on one
 * teacher task at a time so grouping and seating do not teach a shared
 * whole-workspace mental model.
 */

import { computed, onUnmounted, ref, watch } from "vue";

import type { ClassWorkspaceSummary, RoomTemplate, Roster } from "../classroomPlannerTypes";
import PlannerGroupingWorkspacePane from "./PlannerGroupingWorkspacePane.vue";
import PlannerGroupingSettingsDrawer from "./PlannerGroupingSettingsDrawer.vue";
import PlannerGroupingWorkspaceToolbar from "./PlannerGroupingWorkspaceToolbar.vue";
import PlannerHistoryDrawer from "./PlannerHistoryDrawer.vue";
import PlannerRulesWorkspacePane from "./PlannerRulesWorkspacePane.vue";
import PlannerSeatingSettingsDrawer from "./PlannerSeatingSettingsDrawer.vue";
import PlannerSeatingWorkspacePane from "./PlannerSeatingWorkspacePane.vue";
import PlannerSeatingWorkspaceToolbar from "./PlannerSeatingWorkspaceToolbar.vue";
import PlannerTopPanel from "./PlannerTopPanel.vue";
import PlannerWorkspaceModeSurface from "./PlannerWorkspaceModeSurface.vue";
import type { GroupingExportOption, SeatingExportOption } from "../classroomPlannerExportApi";
import { PLANNER_WORKSPACE_SHELL_CLASS } from "../plannerWorkspaceLayout";
import { useClassroomState } from "../useClassroomState";
import { usePlannerUndoRedoShortcuts } from "../usePlannerUndoRedoShortcuts";
import { resolvePlannerWorkspaceDisabledReasons } from "../plannerWorkspacePrerequisites";
import { useHelp } from "../../../components/help/useHelp";
import { useToast } from "../../../composables/useToast";

type PlannerView = "groups" | "seats" | "rules";
type PlannerStatusTone = "neutral" | "success" | "warning" | "danger";

const props = withDefaults(
  defineProps<{
    availableRosters?: Roster[];
    availableTemplates?: RoomTemplate[];
    selectedRosterId?: string | null;
    selectedWorkspaceTemplateId?: string | null;
    initialView?: PlannerView;
    workspaceSummary?: ClassWorkspaceSummary | null;
    seatingLifecycleBusy?: boolean;
    seatingHistoryBusyDraftId?: string | null;
    groupingExportBusy?: boolean;
    groupingExportStatusLabel?: string | null;
    groupingExportErrorMessage?: string | null;
    seatingExportBusy?: boolean;
    seatingExportStatusLabel?: string | null;
    seatingExportErrorMessage?: string | null;
    transitionLabel?: string | null;
    workspaceNotice?: string | null;
  }>(),
  {
    availableRosters: () => [],
    availableTemplates: () => [],
    selectedRosterId: null,
    selectedWorkspaceTemplateId: null,
    initialView: "groups",
    workspaceSummary: null,
    seatingLifecycleBusy: false,
    seatingHistoryBusyDraftId: null,
    groupingExportBusy: false,
    groupingExportStatusLabel: null,
    groupingExportErrorMessage: null,
    seatingExportBusy: false,
    seatingExportStatusLabel: null,
    seatingExportErrorMessage: null,
    transitionLabel: null,
    workspaceNotice: null,
  },
);

const emit = defineEmits<{
  (e: "change-grouping-roster", payload: { rosterId: string }): void;
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
  (e: "export-seating-default"): void;
  (e: "export-seating-option", option: SeatingExportOption): void;
  (e: "edit-current-template", template: RoomTemplate): void;
  (e: "open-rules"): void;
  (e: "select-workspace-mode", mode: "overview" | "grouping" | "seating" | "rules"): void;
  (e: "dismiss-workspace-notice"): void;
  (e: "exit-app"): void;
}>();

const plannerState = useClassroomState();
const toast = useToast();

usePlannerUndoRedoShortcuts({
  plannerState,
  isEnabled: () => !isTransitioningBetweenWorkspaces.value,
});

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
const isGroupingSettingsDrawerOpen = ref(false);
const isSeatingSettingsDrawerOpen = ref(false);
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
const resolvedWorkspaceTemplateId = computed(() => {
  return (
    props.selectedWorkspaceTemplateId
    ?? plannerState.template?.id
    ?? props.workspaceSummary?.active_seating_draft?.template_id
    ?? null
  );
});
const workspaceDisabledReasons = computed(() => {
  return resolvePlannerWorkspaceDisabledReasons({
    hasRoster: plannerState.roster !== null,
    hasTemplate: resolvedWorkspaceTemplateId.value !== null,
  });
});

// Keep the global help panel in sync with the active planner mode.
const { setHelpContext, clearHelpContext } = useHelp();
watch(workspaceModeValue, (mode) => setHelpContext(`planner_${mode}`), { immediate: true });
onUnmounted(() => clearHelpContext(`planner_${workspaceModeValue.value}`));
const isSeatWorkspaceWithoutTemplate = computed(() => {
  return currentView.value === "seats" && plannerState.template === null;
});
const workspaceContextLabel = computed(() => plannerState.template?.name ?? "Utan klassrum");
const topPanelContextLabel = computed(() => {
  return isSeatWorkspaceWithoutTemplate.value
    ? "Välj klassrum i sittschemat"
    : workspaceContextLabel.value;
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
    return "Slumpa eller placera eleverna och dra dem mellan grupperna tills du är nöjd.";
  }
  if (currentView.value === "rules") {
    return "Här ställer du in regler som påverkar hur sittschemat skapas.";
  }
  return "Dra elever till platserna och justera sittschemat direkt i klassrummet.";
});
const displayedPlannerTitle = ref(plannerTitle.value);
const displayedContextLabel = ref(topPanelContextLabel.value);
const displayedSupportingText = ref(currentViewHint.value);
const displayedStatusLabel = ref<string | null>(plannerState.plannerStatusLabel ?? null);
const displayedStatusMessage = ref<string | null>(plannerState.plannerStatusMessage ?? null);
const displayedStatusTone = ref<PlannerStatusTone>(plannerState.plannerStatusTone);
const isTransitioningBetweenWorkspaces = computed(() => Boolean(props.transitionLabel));
const lastWorkspaceNotice = ref<string | null>(null);
const lastGroupingSmartRunToast = ref<string | null>(null);
const lastSeatingSmartRunToast = ref<string | null>(null);

watch(
  [
    plannerTitle,
    topPanelContextLabel,
    currentViewHint,
    () => plannerState.plannerStatusLabel,
    () => plannerState.plannerStatusMessage,
    () => plannerState.plannerStatusTone,
    () => props.transitionLabel,
  ],
  ([
    nextTitle,
    nextContextLabel,
    nextSupportingText,
    nextStatusLabel,
    nextStatusMessage,
    nextStatusTone,
    nextTransitionLabel,
  ]) => {
    if (nextTransitionLabel) {
      return;
    }

    displayedPlannerTitle.value = nextTitle;
    displayedContextLabel.value = nextContextLabel;
    displayedSupportingText.value = nextSupportingText;
    displayedStatusLabel.value = nextStatusLabel;
    displayedStatusMessage.value = nextStatusMessage;
    displayedStatusTone.value = nextStatusTone;
  },
  { immediate: true },
);

function selectStudent(studentId: string): void {
  if (currentView.value === "groups") {
    selectedStudentId.value = null;
    return;
  }

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

function changeSeatingTemplate(templateId: string | null): void {
  pendingSeatingTemplateId.value = templateId ?? "";
  emit("change-seating-template", { templateId });
}

function changeGroupingTemplate(templateId: string | null): void {
  pendingGroupingTemplateId.value = templateId ?? "";
  emit("change-grouping-template", { templateId });
}

function changeGroupingRoster(rosterId: string): void {
  emit("change-grouping-roster", { rosterId });
}

function startNewGroupingDraft(): void {
  emit("new-grouping-draft", { templateId: plannerState.template?.id ?? null });
}

function openGroupingHistoryDrawer(): void {
  openHistoryDrawerKind.value = "grouping";
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
    isGroupingSettingsDrawerOpen.value = false;
    isSeatingSettingsDrawerOpen.value = false;
    openHistoryDrawerKind.value = null;
    selectedStudentId.value = null;
  },
);

watch(
  () => [plannerState.draft?.draft_kind ?? null, plannerState.template?.id ?? null],
  () => {
    currentView.value = resolvePlannerView(currentView.value);
    isGroupingSettingsDrawerOpen.value = false;
    isSeatingSettingsDrawerOpen.value = false;
    openHistoryDrawerKind.value = null;
    selectedStudentId.value = null;
    pendingGroupingTemplateId.value = plannerState.template?.id ?? "";
    pendingSeatingTemplateId.value = plannerState.template?.id ?? "";
  },
);

watch(
  () => props.workspaceNotice,
  (nextNotice) => {
    if (!nextNotice) {
      lastWorkspaceNotice.value = null;
      return;
    }
    if (nextNotice === lastWorkspaceNotice.value) {
      return;
    }
    toast.info(nextNotice);
    lastWorkspaceNotice.value = nextNotice;
    emit("dismiss-workspace-notice");
  },
  { immediate: true },
);

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
        @click="reloadAfterConflict"
      >
        Ladda om utkast
      </button>
    </div>

    <PlannerTopPanel
      :title="displayedPlannerTitle"
      :context-label="displayedContextLabel"
      :mode-value="workspaceModeValue"
      :grouping-disabled-reason="workspaceDisabledReasons.grouping"
      :seating-disabled-reason="workspaceDisabledReasons.seating"
      :rules-disabled-reason="workspaceDisabledReasons.rules"
      :supporting-text="displayedSupportingText"
      :status-label="displayedStatusLabel"
      :status-message="displayedStatusMessage"
      :status-tone="displayedStatusTone"
      @update:mode-value="selectWorkspaceMode"
      @exit="emit('exit-app')"
    />

    <div
      v-if="transitionLabel"
      class="border border-navy bg-white px-4 py-10 text-center text-sm font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy shadow-brutal-sm"
      data-test="planner-workspace-transition"
    >
      {{ transitionLabel }}
    </div>

    <template v-if="!isTransitioningBetweenWorkspaces">
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
            @change-grouping-roster="changeGroupingRoster($event)"
            @new-grouping-draft="startNewGroupingDraft"
            @open-settings="openGroupingSettingsDrawer"
            @open-history="openGroupingHistoryDrawer"
            @open-rules="emit('open-rules')"
            @edit-roster="emit('edit-roster')"
            @export-default="emit('export-grouping-default')"
            @export-option="emit('export-grouping-option', $event)"
          />
        </template>

        <PlannerGroupingWorkspacePane />
      </PlannerWorkspaceModeSurface>

      <PlannerWorkspaceModeSurface
        v-if="currentView === 'seats'"
        view="seats"
      >
        <template #toolbar>
          <PlannerSeatingWorkspaceToolbar
            :available-templates="availableTemplates"
            :selected-template-id="pendingSeatingTemplateId"
            :smart-settings-open="isSeatingSettingsDrawerOpen"
            :seating-lifecycle-busy="seatingLifecycleBusy"
            :export-busy="seatingExportBusy"
            :export-status-label="seatingExportStatusLabel"
            :export-error-message="seatingExportErrorMessage"
            @change-seating-template="changeSeatingTemplate($event)"
            @new-seating-draft="emit('new-seating-draft', { templateId: $event })"
            @export-default="emit('export-seating-default')"
            @export-option="emit('export-seating-option', $event)"
            @edit-roster="emit('edit-roster')"
            @edit-current-template="editCurrentTemplate"
            @open-settings="openSeatingSettingsDrawer"
            @open-history="openSeatingHistoryDrawer"
          />
        </template>

        <PlannerSeatingWorkspacePane
          :selected-template-id="pendingSeatingTemplateId"
        />
      </PlannerWorkspaceModeSurface>

      <PlannerRulesWorkspacePane
        v-if="currentView === 'rules'"
        :selected-student-id="selectedStudentId"
        @student-selected="selectStudent"
      />

      <PlannerGroupingSettingsDrawer
        :open="currentView === 'groups' && isGroupingSettingsDrawerOpen"
        :available-templates="availableTemplates"
        :selected-template-id="pendingGroupingTemplateId"
        @close="closeGroupingSettingsDrawer"
        @change-grouping-template="changeGroupingTemplate($event)"
        @open-rules="emit('open-rules')"
      />

      <PlannerSeatingSettingsDrawer
        :open="currentView === 'seats' && isSeatingSettingsDrawerOpen"
        @close="closeSeatingSettingsDrawer"
        @open-rules="emit('open-rules')"
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
    </template>
  </section>
</template>
