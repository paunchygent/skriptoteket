<script setup lang="ts">
/**
 * Seating workspace pane.
 *
 * This component composes the seating-only setup row, action row, student
 * pool, and room canvas. It keeps seating-specific lifecycle affordances out
 * of the global planner shell while preserving the existing teacher workflow.
 */

import { computed, nextTick, ref, watch } from "vue";

import { IconHistory, IconRedo, IconSettings, IconShuffle, IconUndo } from "../../../components/icons";
import type { RoomTemplate } from "../classroomPlannerTypes";
import { getRoomSurfaceMetrics } from "../roomFixturePresentation";
import { normalizeRoomGrid } from "../roomFixtureLayout";
import { useRoomViewportZoom } from "../useRoomViewportZoom";
import PlannerConfirmationDialog from "./PlannerConfirmationDialog.vue";
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
  }>(),
  {
    selectedStudentId: null,
    availableTemplates: () => [],
    selectedTemplateId: null,
    seatingLifecycleBusy: false,
  },
);

const emit = defineEmits<{
  (e: "student-selected", studentId: string): void;
  (e: "change-seating-template", templateId: string | null): void;
  (e: "new-seating-draft", templateId: string): void;
  (e: "edit-current-template", template: RoomTemplate): void;
  (e: "open-history"): void;
}>();

const plannerState = useClassroomState();
const seatingTemplateSelect = ref<HTMLSelectElement | null>(null);
const showSeatingTemplateRequiredHint = ref(false);
const isResetSeatingDialogOpen = ref(false);

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
const canRandomizeSeating = computed(() => {
  return (
    plannerState.template !== null
    && plannerState.students.length > 0
    && plannerState.seats.length > 0
    && !plannerState.isWorkspaceBusy
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
    icon: IconSettings,
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

function randomizeCurrentSeatingDraft(): void {
  if (!canRandomizeSeating.value) {
    return;
  }
  plannerState.randomizeSeating();
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

watch(
  () => props.selectedTemplateId,
  () => {
    showSeatingTemplateRequiredHint.value = false;
  },
);
</script>

<template>
  <div class="grid gap-5 xl:grid-cols-[280px_minmax(0,1fr)]">
    <PlannerStudentPool
      title="Ej placerade"
      :students="plannerState.unseatedStudents"
      :selected-student-id="selectedStudentId"
      empty-label="Alla elever har fått plats"
      root-test-id="seating-student-pool"
      @student-selected="emit('student-selected', $event)"
      @student-dragstart="onStudentDragStart($event.event, $event.studentId)"
      @pool-dragover="onDragOver"
      @pool-drop="onDropToPool"
    />

    <section class="space-y-4">
      <PlannerWorkspaceActionBar>
        <template #leading>
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

        <PlannerToolbarIconButton
          label="Ångra"
          class="2xl:hidden"
          data-test="undo-seating-draft"
          :disabled="!plannerState.canUndo || seatingLifecycleBusy"
          @click="void undoSeatingDraft()"
        >
          <IconUndo :size="18" />
        </PlannerToolbarIconButton>
        <button
          type="button"
          class="btn-ghost hidden border-navy/30 bg-white shadow-none 2xl:inline-flex"
          :disabled="!plannerState.canUndo || seatingLifecycleBusy"
          @click="void undoSeatingDraft()"
        >
          Ångra
        </button>
        <PlannerToolbarIconButton
          label="Gör om"
          class="2xl:hidden"
          data-test="redo-seating-draft"
          :disabled="!plannerState.canRedo || seatingLifecycleBusy"
          @click="void redoSeatingDraft()"
        >
          <IconRedo :size="18" />
        </PlannerToolbarIconButton>
        <button
          type="button"
          class="btn-ghost hidden border-navy/30 bg-white shadow-none 2xl:inline-flex"
          :disabled="!plannerState.canRedo || seatingLifecycleBusy"
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
          :disabled="seatingLifecycleBusy || plannerState.isWorkspaceBusy || !hasSeatingAssignments"
          @click="openResetSeatingDialog"
        >
          Börja om
        </button>
        <button
          type="button"
          class="btn-ghost border-navy/30 bg-white shadow-none"
          data-test="new-seating-draft"
          :disabled="seatingLifecycleBusy"
          @click="void startNewSeatingDraft()"
        >
          Nytt sittschema
        </button>
        <PlannerToolbarOverflowMenu
          label="Fler sittplatsåtgärder"
          :items="secondaryActionItems"
          test-id="seating-actions-menu"
        />
      </PlannerWorkspaceActionBar>

      <RoomCanvas
        v-if="!isSeatWorkspaceWithoutTemplate"
        data-test="seating-workspace"
        :scale-percent="seatingCanvasScalePercent"
        :scaled-surface-style="seatingCanvasScaledSurfaceStyle"
        :selected-student-id="selectedStudentId"
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
  </div>
</template>
