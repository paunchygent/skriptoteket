<script setup lang="ts">
/**
 * Planner workspace shell.
 *
 * This component renders the active classroom-planning workspace after a draft
 * has been created or resumed. It keeps the default surface focused on one
 * teacher task at a time so grouping and seating do not teach a shared
 * whole-workspace mental model.
 */

import { computed, nextTick, ref, watch } from "vue";

import { IconHistory, IconRedo, IconSettings, IconShuffle, IconUndo } from "../../../components/icons";
import type { ClassWorkspaceSummary, RoomTemplate } from "../classroomPlannerTypes";
import GroupBoard from "./GroupBoard.vue";
import PlannerConfirmationDialog from "./PlannerConfirmationDialog.vue";
import PlannerHistoryDrawer from "./PlannerHistoryDrawer.vue";
import PlannerMetadataDrawer from "./PlannerMetadataDrawer.vue";
import PlannerTopPanel from "./PlannerTopPanel.vue";
import PlannerToolbarIconButton from "./PlannerToolbarIconButton.vue";
import PlannerToolbarOverflowMenu from "./PlannerToolbarOverflowMenu.vue";
import RoomCanvas from "./RoomCanvas.vue";
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
  (e: "exit-to-landing"): void;
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
const pendingGroupingTemplateId = ref("");
const pendingSeatingTemplateId = ref("");
const seatingTemplateSelect = ref<HTMLSelectElement | null>(null);
const showSeatingTemplateRequiredHint = ref(false);
const isResetSeatingDialogOpen = ref(false);
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
const canEditCurrentTemplate = computed(() => currentView.value === "seats" && plannerState.template !== null);
const canRandomizeSeating = computed(() => {
  return (
    currentView.value === "seats"
    && plannerState.template !== null
    && plannerState.students.length > 0
    && plannerState.seats.length > 0
    && !plannerState.isWorkspaceBusy
    && !props.seatingLifecycleBusy
  );
});
const hasSeatingAssignments = computed(() => plannerState.seatAssignments.length > 0);
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
const seatingSecondaryActionItems = computed(() => [
  {
    id: "history",
    label: "Historik",
    icon: IconHistory,
    disabled: props.seatingLifecycleBusy,
    testId: "seating-history",
    onSelect: openSeatingHistoryDrawer,
  },
  {
    id: "edit-template",
    label: "Redigera klassrum",
    icon: IconSettings,
    disabled: !canEditCurrentTemplate.value || plannerState.isWorkspaceBusy || props.seatingLifecycleBusy,
    testId: "edit-current-template",
    onSelect: editCurrentTemplate,
  },
]);

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

function changeSeatingTemplateFromEvent(event: Event): void {
  const target = event.target;
  if (!(target instanceof HTMLSelectElement)) {
    return;
  }

  showSeatingTemplateRequiredHint.value = false;
  pendingSeatingTemplateId.value = target.value;
  emit("change-seating-template", { templateId: pendingSeatingTemplateId.value || null });
}

function changeGroupingTemplate(templateId: string | null): void {
  pendingGroupingTemplateId.value = templateId ?? "";
  emit("change-grouping-template", { templateId });
}

function startNewGroupingDraft(): void {
  emit("new-grouping-draft", { templateId: plannerState.template?.id ?? null });
}

async function startNewSeatingDraft(): Promise<void> {
  if (props.seatingLifecycleBusy) {
    return;
  }
  if (!plannerState.template?.id) {
    showSeatingTemplateRequiredHint.value = true;
    await nextTick();
    seatingTemplateSelect.value?.focus();
    return;
  }

  showSeatingTemplateRequiredHint.value = false;
  emit("new-seating-draft", { templateId: plannerState.template.id });
}

async function undoSeatingDraft(): Promise<void> {
  if (props.seatingLifecycleBusy) {
    return;
  }
  await plannerState.undoSeatingDraft();
}

async function redoSeatingDraft(): Promise<void> {
  if (props.seatingLifecycleBusy) {
    return;
  }
  await plannerState.redoSeatingDraft();
}

function randomizeCurrentSeatingDraft(): void {
  if (!canRandomizeSeating.value) {
    return;
  }
  plannerState.randomizeSeating();
}

function openResetSeatingDialog(): void {
  if (props.seatingLifecycleBusy || plannerState.isWorkspaceBusy || !hasSeatingAssignments.value) {
    return;
  }
  isResetSeatingDialogOpen.value = true;
}

function closeResetSeatingDialog(): void {
  isResetSeatingDialogOpen.value = false;
}

function confirmResetSeatingDraft(): void {
  plannerState.clearSeatingAssignments();
  closeResetSeatingDialog();
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

function editCurrentTemplate(): void {
  if (plannerState.template) {
    emit("edit-current-template", plannerState.template);
  }
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
    showSeatingTemplateRequiredHint.value = false;
    isResetSeatingDialogOpen.value = false;
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
    showSeatingTemplateRequiredHint.value = false;
    isResetSeatingDialogOpen.value = false;
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
      @exit="emit('exit-to-landing')"
    />

    <GroupBoard
      v-if="currentView === 'groups'"
      :selected-student-id="selectedStudentId"
      :available-templates="availableTemplates"
      :selected-template-id="plannerState.template?.id ?? pendingGroupingTemplateId"
      @new-grouping-draft="startNewGroupingDraft"
      @open-history="openGroupingHistoryDrawer"
      @edit-roster="emit('edit-roster')"
      @student-selected="selectStudent"
      @change-grouping-template="changeGroupingTemplate"
    />
    <section
      v-if="currentView === 'seats'"
      class="space-y-4"
    >
      <div class="flex flex-wrap items-end justify-end gap-2 border border-navy bg-white p-4 shadow-brutal-sm">
        <label
          class="block min-w-[16rem] space-y-1"
          data-test="seating-workspace-setup"
        >
          <span class="block text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
            Klassrum
          </span>
          <select
            ref="seatingTemplateSelect"
            data-test="seating-template-select"
            class="w-full border border-navy/20 bg-white px-3 py-2 text-sm text-navy"
            :value="plannerState.template?.id ?? pendingSeatingTemplateId"
            @change="changeSeatingTemplateFromEvent"
          >
            <option value="">
              Välj klassrum
            </option>
            <option
              v-for="template in availableTemplates"
              :key="template.id"
              :value="template.id"
            >
              {{ template.name }} · {{ template.seats.length }} platser
            </option>
          </select>
          <p
            v-if="showSeatingTemplateRequiredHint"
            class="text-xs font-semibold text-burgundy"
          >
            Välj klassrum innan du startar ett nytt sittschema.
          </p>
        </label>
        <PlannerToolbarIconButton
          label="Ångra"
          class="2xl:hidden"
          data-test="undo-seating-draft"
          :disabled="!plannerState.canUndo || props.seatingLifecycleBusy"
          @click="void undoSeatingDraft()"
        >
          <IconUndo :size="18" />
        </PlannerToolbarIconButton>
        <button
          type="button"
          class="btn-ghost hidden border-navy/30 bg-white shadow-none 2xl:inline-flex"
          :disabled="!plannerState.canUndo || props.seatingLifecycleBusy"
          @click="void undoSeatingDraft()"
        >
          Ångra
        </button>
        <PlannerToolbarIconButton
          label="Gör om"
          class="2xl:hidden"
          data-test="redo-seating-draft"
          :disabled="!plannerState.canRedo || props.seatingLifecycleBusy"
          @click="void redoSeatingDraft()"
        >
          <IconRedo :size="18" />
        </PlannerToolbarIconButton>
        <button
          type="button"
          class="btn-ghost hidden border-navy/30 bg-white shadow-none 2xl:inline-flex"
          :disabled="!plannerState.canRedo || props.seatingLifecycleBusy"
          @click="void redoSeatingDraft()"
        >
          Gör om
        </button>
        <button
          type="button"
          class="btn-ghost inline-flex items-center gap-2 border-navy/30 bg-white shadow-none disabled:cursor-not-allowed disabled:border-navy/15 disabled:text-navy/35"
          data-test="randomize-seating"
          :disabled="!canRandomizeSeating"
          @click="randomizeCurrentSeatingDraft"
        >
          <IconShuffle :size="16" />
          <span>Slumpa</span>
        </button>
        <button
          type="button"
          class="btn-ghost border-navy/30 bg-white shadow-none disabled:cursor-not-allowed disabled:border-navy/15 disabled:text-navy/35"
          data-test="reset-seating-draft"
          :disabled="props.seatingLifecycleBusy || plannerState.isWorkspaceBusy || !hasSeatingAssignments"
          @click="openResetSeatingDialog"
        >
          Börja om
        </button>
        <button
          type="button"
          class="btn-ghost border-navy/30 bg-white shadow-none"
          data-test="new-seating-draft"
          :disabled="props.seatingLifecycleBusy"
          @click="void startNewSeatingDraft()"
        >
          Nytt sittschema
        </button>
        <PlannerToolbarOverflowMenu
          label="Fler sittplatsåtgärder"
          :items="seatingSecondaryActionItems"
          test-id="seating-actions-menu"
        />
      </div>

      <RoomCanvas
        v-if="!isSeatWorkspaceWithoutTemplate"
        data-test="seating-workspace"
        :selected-student-id="selectedStudentId"
        @student-selected="selectStudent"
      />
      <div
        v-else
        class="border border-dashed border-navy/30 bg-canvas px-6 py-8 text-center text-sm leading-relaxed text-navy/70"
      >
        Välj ett klassrum ovan för att börja placera sittplatser. Du kan byta klassrum här senare utan att lämna sittschemat.
      </div>
    </section>

    <PlannerConfirmationDialog
      v-if="isResetSeatingDialogOpen"
      eyebrow="Börja om sittschema"
      title="Töm sittplaceringarna?"
      message="Det här rensar sittplaceringarna i det aktuella sittschemat och flyttar tillbaka alla elever till Ej placerade. Själva utkastet och klassrummet finns kvar."
      confirm-label="Börja om"
      @cancel="closeResetSeatingDialog"
      @confirm="confirmResetSeatingDraft"
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
