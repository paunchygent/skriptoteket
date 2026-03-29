<script setup lang="ts">
/**
 * Seating workspace pane.
 *
 * This component now stays focused on the student pool, canvas, and blocking
 * local error surfaces after ST-29-02 moved the toolbar into the shared
 * planner shell. It avoids reintroducing full-width transient feedback bands
 * between the toolbar and the seating canvas.
 */

import { computed } from "vue";

import { buildSmartRuleMarkersByStudentId } from "../classroomPlannerSmartRulePresentation";
import { getRoomSurfaceMetrics } from "../roomFixturePresentation";
import { setSeatStyledStudentDragPreview } from "../roomSeatDragPreview";
import { normalizeRoomGrid } from "../roomFixtureLayout";
import { useRoomViewportZoom } from "../useRoomViewportZoom";
import PlannerStudentPool from "./PlannerStudentPool.vue";
import RoomCanvas from "./RoomCanvas.vue";
import { useClassroomState } from "../useClassroomState";

const {
  selectedStudentId = null,
  selectedTemplateId = null,
} = defineProps<{
  selectedStudentId?: string | null;
  selectedTemplateId?: string | null;
}>();

const emit = defineEmits<{
  (e: "student-selected", studentId: string): void;
}>();

const plannerState = useClassroomState();

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
  resetSource: computed(() => selectedTemplateId ?? plannerState.template?.id ?? null),
});
const smartRuleMarkersByStudentId = computed<Record<string, string[]>>(() => {
  return buildSmartRuleMarkersByStudentId(
    plannerState.seatingPreferences,
    plannerState.relationshipRules,
  );
});

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
</script>

<template>
  <div class="flex flex-col gap-3">
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
  </div>
</template>
