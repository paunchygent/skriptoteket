<script setup lang="ts">
/**
 * Seating workspace pane.
 *
 * This component composes the seating-only setup row, action row, student
 * pool, and room canvas. It keeps seating-specific lifecycle affordances out
 * of the global planner shell while preserving the existing teacher workflow.
 */

import { computed, nextTick, ref, watch } from "vue";

import { IconAdjustments, IconHistory, IconRedo, IconShuffle, IconUndo, IconX } from "../../../components/icons";
import {
  DENSE_FORM_INPUT_CLASS,
  UiDenseActionButton,
  UiDenseCompoundToggle,
  UiDenseToggle,
} from "../../../components/ui";
import type { SeatingExportOption } from "../classroomPlannerExportApi";
import type { RoomTemplate, Student } from "../classroomPlannerTypes";
import { buildSmartRuleMarkersByStudentId } from "../classroomPlannerSmartRulePresentation";
import { getRoomSurfaceMetrics } from "../roomFixturePresentation";
import { setSeatStyledStudentDragPreview } from "../roomSeatDragPreview";
import { normalizeRoomGrid } from "../roomFixtureLayout";
import { useRoomViewportZoom } from "../useRoomViewportZoom";
import PlannerConfirmationDialog from "./PlannerConfirmationDialog.vue";
import PlannerExportActionGroup, { type PlannerExportOptionValue } from "./PlannerExportActionGroup.vue";
import PlannerSmartRulesSummaryStrip from "./PlannerSmartRulesSummaryStrip.vue";
import PlannerStudentPool from "./PlannerStudentPool.vue";
import PlannerToolbarIconButton from "./PlannerToolbarIconButton.vue";
import PlannerToolbarOverflowMenu from "./PlannerToolbarOverflowMenu.vue";
import PlannerWorkspaceActionBar from "./PlannerWorkspaceActionBar.vue";
import RoomCanvas from "./RoomCanvas.vue";
import { useClassroomState } from "../useClassroomState";

const props = withDefaults(
  defineProps<{
    selectedStudentId?: string | null;
    availableTemplates?: RoomTemplate[];
    selectedTemplateId?: string | null;
    seatingLifecycleBusy?: boolean;
    exportBusy?: boolean;
    exportStatusLabel?: string | null;
    exportErrorMessage?: string | null;
    canDownloadLatestExport?: boolean;
  }>(),
  {
    selectedStudentId: null,
    availableTemplates: () => [],
    selectedTemplateId: null,
    seatingLifecycleBusy: false,
    exportBusy: false,
    exportStatusLabel: null,
    exportErrorMessage: null,
    canDownloadLatestExport: false,
  },
);

const emit = defineEmits<{
  (e: "student-selected", studentId: string): void;
  (e: "change-seating-template", templateId: string | null): void;
  (e: "new-seating-draft", templateId: string): void;
  (e: "edit-current-template", template: RoomTemplate): void;
  (e: "open-history"): void;
  (e: "open-rules"): void;
  (e: "export-default"): void;
  (e: "export-option", option: SeatingExportOption): void;
  (e: "download-latest-export"): void;
}>();

const plannerState = useClassroomState();
const seatingTemplateSelect = ref<HTMLSelectElement | null>(null);
const showSeatingTemplateRequiredHint = ref(false);
const isResetSeatingDialogOpen = ref(false);
const isExportStatusDismissed = ref(false);

const isSeatWorkspaceWithoutTemplate = computed(() => plannerState.template === null);
const seatingRoomGrid = computed(() => normalizeRoomGrid(plannerState.template));
const seatingRoomSurfaceMetrics = computed(() => getRoomSurfaceMetrics(seatingRoomGrid.value));
const {
  scale: seatingCanvasScale,
  scaledSurfaceStyle: seatingCanvasScaledSurfaceStyle,
  scalePercent: seatingCanvasScalePercent,
  setViewportSize: setSeatingCanvasViewportSize,
  zoomOut: zoomOutSeatingCanvas,
  zoomIn: zoomInSeatingCanvas,
  resetZoom: resetSeatingCanvasZoom,
} = useRoomViewportZoom(seatingRoomSurfaceMetrics, {
  resetSource: computed(() => props.selectedTemplateId ?? plannerState.template?.id ?? null),
});
const canEditCurrentTemplate = computed(() => plannerState.template !== null);
const nearTeacherStudents = computed<Student[]>(() => {
  return (plannerState.seatingPreferences ?? [])
    .filter((preference) => preference.near_teacher === true)
    .map((preference) => plannerState.studentsById[preference.student_id] ?? null)
    .filter((student): student is Student => student !== null);
});
const smartRuleMarkersByStudentId = computed<Record<string, string[]>>(() => {
  return buildSmartRuleMarkersByStudentId(
    plannerState.seatingPreferences,
    plannerState.relationshipRules,
  );
});
const canRandomizeSeating = computed(() => {
  return (
    plannerState.template !== null
    && plannerState.students.length > 0
    && plannerState.seats.length > 0
    && !plannerState.isWorkspaceBusy
    && !plannerState.isRunningSmartSeating
    && !props.seatingLifecycleBusy
  );
});
const hasSeatingAssignments = computed(() => plannerState.seatAssignments.length > 0);
const secondaryActionItems = computed(() => [
  {
    id: "history",
    label: "Historik",
    icon: IconHistory,
    disabled: props.seatingLifecycleBusy,
    testId: "seating-history",
    onSelect: () => emit("open-history"),
  },
  {
    id: "edit-template",
    label: "Redigera klassrum",
    icon: IconAdjustments,
    disabled: !canEditCurrentTemplate.value || plannerState.isWorkspaceBusy || props.seatingLifecycleBusy,
    testId: "edit-current-template",
    onSelect: editCurrentTemplate,
  },
]);

async function startNewSeatingDraft(): Promise<void> {
  if (props.seatingLifecycleBusy) {
    return;
  }
  if (!props.selectedTemplateId) {
    showSeatingTemplateRequiredHint.value = true;
    await nextTick();
    seatingTemplateSelect.value?.focus();
    return;
  }

  showSeatingTemplateRequiredHint.value = false;
  emit("new-seating-draft", props.selectedTemplateId);
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

async function randomizeCurrentSeatingDraft(): Promise<void> {
  if (!canRandomizeSeating.value) {
    return;
  }
  await plannerState.runSeatingShuffle();
}

function changeSeatingTemplateFromEvent(event: Event): void {
  const target = event.target;
  if (!(target instanceof HTMLSelectElement)) {
    return;
  }

  showSeatingTemplateRequiredHint.value = false;
  emit("change-seating-template", target.value || null);
}

function onStudentDragStart(event: DragEvent, studentId: string): void {
  if (event.dataTransfer) {
    event.dataTransfer.setData("studentId", studentId);
    event.dataTransfer.effectAllowed = "move";
  }

  const student = plannerState.studentsById[studentId];
  if (!student) {
    return;
  }
  setSeatStyledStudentDragPreview(event, student.display_name);
}

function onDropToPool(event: DragEvent): void {
  event.preventDefault();
  const studentId = event.dataTransfer?.getData("studentId");
  if (studentId) {
    plannerState.clearSeatAssignment(studentId);
  }
}

function onDragOver(event: DragEvent): void {
  event.preventDefault();
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = "move";
  }
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

function editCurrentTemplate(): void {
  if (plannerState.template) {
    emit("edit-current-template", plannerState.template);
  }
}

function handleExportOption(option: PlannerExportOptionValue): void {
  emit("export-option", option as SeatingExportOption);
}

watch(
  () => props.selectedTemplateId,
  () => {
    showSeatingTemplateRequiredHint.value = false;
  },
);

watch(
  () => [props.exportStatusLabel, props.exportErrorMessage, props.canDownloadLatestExport] as const,
  () => {
    isExportStatusDismissed.value = false;
  },
);
</script>

<template>
  <div class="flex flex-col gap-3">
    <PlannerWorkspaceActionBar>
      <template #leading>
        <label
          class="block w-[12rem]"
          data-test="seating-workspace-setup"
        >
          <select
            ref="seatingTemplateSelect"
            data-test="seating-template-select"
            aria-label="Klassrum"
            :class="[DENSE_FORM_INPUT_CLASS, 'pr-8']"
            :value="selectedTemplateId ?? ''"
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
      </template>

      <div
        class="flex items-center [&>*+*]:-ml-px"
        data-test="seating-history-cluster"
      >
        <PlannerToolbarIconButton
          label="Ångra"
          size="utility"
          group-position="start"
          data-test="undo-seating-draft"
          :disabled="!plannerState.canUndo || seatingLifecycleBusy"
          @click="void undoSeatingDraft()"
        >
          <IconUndo :size="16" />
        </PlannerToolbarIconButton>
        <PlannerToolbarIconButton
          label="Gör om"
          size="utility"
          group-position="end"
          data-test="redo-seating-draft"
          :disabled="!plannerState.canRedo || seatingLifecycleBusy"
          @click="void redoSeatingDraft()"
        >
          <IconRedo :size="16" />
        </PlannerToolbarIconButton>
      </div>
      <UiDenseActionButton
        label="Slumpa"
        data-test="randomize-seating"
        :disabled="!canRandomizeSeating"
        @click="void randomizeCurrentSeatingDraft()"
      >
        <template #leading>
          <IconShuffle :size="16" />
        </template>
      </UiDenseActionButton>
      <UiDenseCompoundToggle
        root-test-id="seating-smart-toggle"
        label="Smart"
        :model-value="plannerState.draft?.smart_enabled ?? false"
        :disabled="plannerState.isWorkspaceBusy || seatingLifecycleBusy"
        action-label="Regler"
        action-title="Öppna regler"
        :action-disabled="plannerState.isWorkspaceBusy || seatingLifecycleBusy"
        action-test-id="seating-open-rules"
        @update:model-value="plannerState.setDraftSmartEnabled($event)"
        @action="emit('open-rules')"
      />
      <UiDenseActionButton
        label="Börja om"
        data-test="reset-seating-draft"
        :disabled="seatingLifecycleBusy || plannerState.isWorkspaceBusy || !hasSeatingAssignments"
        tone="danger"
        @click="openResetSeatingDialog"
      >
        Börja om
      </UiDenseActionButton>
      <UiDenseActionButton
        label="Nytt sittschema"
        data-test="new-seating-draft"
        :disabled="seatingLifecycleBusy"
        @click="void startNewSeatingDraft()"
      />
      <PlannerExportActionGroup
        :busy="exportBusy"
        @export-default="emit('export-default')"
        @export-option="handleExportOption"
      />
      <PlannerToolbarOverflowMenu
        label="Fler sittplatsåtgärder"
        :items="secondaryActionItems"
        test-id="seating-actions-menu"
      />
    </PlannerWorkspaceActionBar>

    <p
      v-if="plannerState.smartSeatingRunMessage"
      class="border px-3 py-2 text-sm font-semibold"
      :class="
        plannerState.smartSeatingRunTone === 'success'
          ? 'border-emerald-300 bg-emerald-50 text-emerald-900'
          : 'border-amber-300 bg-amber-50 text-amber-900'
      "
      data-test="seating-smart-run-message"
    >
      {{ plannerState.smartSeatingRunMessage }}
    </p>

    <div
      v-if="plannerState.smartRuleHydrationStatus === 'error'"
      class="border border-amber-300/80 bg-amber-50 px-4 py-3 text-sm text-amber-900 shadow-brutal-sm"
      data-test="seating-smart-hydration-error"
    >
      <div class="flex flex-wrap items-center justify-between gap-3">
        <p>
          {{ plannerState.smartRuleHydrationMessage }}
        </p>
        <button
          type="button"
          class="btn-ghost planner-btn-alert planner-btn-ghost-sm"
          data-test="seating-smart-retry-hydration"
          @click="void plannerState.retrySmartRuleHydration()"
        >
          Försök igen
        </button>
      </div>
    </div>

    <div
      v-if="!isExportStatusDismissed && (exportStatusLabel || exportErrorMessage || canDownloadLatestExport)"
      class="flex flex-wrap items-center gap-x-4 gap-y-1 border border-navy/30 bg-white px-3 py-2 text-xs"
      data-test="seating-export-status-bar"
    >
      <p
        v-if="exportStatusLabel"
        class="text-navy"
        data-test="seating-export-status"
      >
        {{ exportStatusLabel }}
      </p>
      <p
        v-if="exportErrorMessage"
        class="font-semibold text-burgundy"
        data-test="seating-export-error"
      >
        {{ exportErrorMessage }}
      </p>
      <button
        v-if="canDownloadLatestExport"
        type="button"
        class="planner-link-button"
        data-test="seating-export-download-latest"
        @click="emit('download-latest-export')"
      >
        Ladda ned igen
      </button>
      <button
        type="button"
        class="planner-icon-dismiss"
        aria-label="Stäng exportstatus"
        data-test="seating-export-status-dismiss"
        @click="isExportStatusDismissed = true"
      >
        <IconX :size="14" />
      </button>
    </div>

    <PlannerSmartRulesSummaryStrip
      :near-teacher-students="nearTeacherStudents"
      :relationship-rules="plannerState.relationshipRules"
      :students-by-id="plannerState.studentsById"
    >
      <template #controls>
        <UiDenseToggle
          data-test="seating-use-history-toggle"
          label="Använd historik"
          :model-value="plannerState.draft?.use_history ?? false"
          :disabled="plannerState.isWorkspaceBusy || seatingLifecycleBusy"
          @update:model-value="plannerState.setDraftUseHistoryEnabled($event)"
        />
      </template>
    </PlannerSmartRulesSummaryStrip>

    <div class="grid gap-3 xl:grid-cols-[240px_minmax(0,1fr)] xl:items-stretch">
      <PlannerStudentPool
        title="Ej placerade"
        :students="plannerState.unseatedStudents"
        :selected-student-id="selectedStudentId"
        :selected-student-ids="plannerState.pendingRelationshipStudentIds"
        :smart-rule-markers-by-student-id="smartRuleMarkersByStudentId"
        empty-label="Alla elever har fått plats"
        root-test-id="seating-student-pool"
        @student-selected="emit('student-selected', $event)"
        @student-dragstart="onStudentDragStart($event.event, $event.studentId)"
        @pool-dragover="onDragOver"
        @pool-drop="onDropToPool"
      />

      <div>
        <RoomCanvas
          v-if="!isSeatWorkspaceWithoutTemplate"
          data-test="seating-workspace"
          :scale-percent="seatingCanvasScalePercent"
          :scaled-surface-style="seatingCanvasScaledSurfaceStyle"
          :selected-student-id="selectedStudentId"
          :selected-student-ids="plannerState.pendingRelationshipStudentIds"
          :smart-rule-markers-by-student-id="smartRuleMarkersByStudentId"
          :surface-scale="seatingCanvasScale"
          @student-selected="emit('student-selected', $event)"
          @viewport-size="setSeatingCanvasViewportSize"
          @zoom-fit="resetSeatingCanvasZoom"
          @zoom-in="zoomInSeatingCanvas"
          @zoom-out="zoomOutSeatingCanvas"
        />
        <div
          v-else
          class="border border-dashed border-navy/30 bg-canvas px-6 py-8 text-center text-sm leading-relaxed text-navy/70"
        >
          Välj ett klassrum ovan för att börja placera sittplatser. Du kan byta klassrum här senare utan att lämna sittschemat.
        </div>
      </div>
    </div>

    <PlannerConfirmationDialog
      v-if="isResetSeatingDialogOpen"
      eyebrow="Börja om sittschema"
      title="Töm sittplaceringarna?"
      message="Det här rensar sittplaceringarna i det aktuella sittschemat och flyttar tillbaka alla elever till Ej placerade. Själva utkastet och klassrummet finns kvar."
      confirm-label="Börja om"
      @cancel="closeResetSeatingDialog"
      @confirm="confirmResetSeatingDraft"
    />
  </div>
</template>
