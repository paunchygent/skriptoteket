<script setup lang="ts">
/**
 * Seating workspace pane.
 *
 * This component now stays focused on the student pool, canvas, and blocking
 * local error surfaces after ST-29-02 moved the toolbar into the shared
 * planner shell. It avoids reintroducing full-width transient feedback bands
 * between the toolbar and the seating canvas.
 */

import { computed, ref } from "vue";

import { IconArrow, IconStudents } from "../../../components/icons";
import { buildSmartRuleMarkersByStudentId } from "../classroomPlannerSmartRulePresentation";
import { getRoomSurfaceMetrics } from "../roomFixturePresentation";
import {
  PLANNER_SEATING_LAYOUT_ROW_CLASS,
  PLANNER_SEATING_STUDENT_POOL_LANE_CLASS,
  PLANNER_SEATING_WORKSPACE_LANE_CLASS,
} from "../plannerWorkspaceLayout";
import { setSeatStyledStudentDragPreview } from "../roomSeatDragPreview";
import { normalizeRoomGrid } from "../roomFixtureLayout";
import { useRoomViewportZoom } from "../useRoomViewportZoom";
import PlannerStudentPool from "./PlannerStudentPool.vue";
import RoomCanvas from "./RoomCanvas.vue";
import { useClassroomState } from "../useClassroomState";
import type { RoomViewportSize } from "../roomBuilderViewport";

const {
  selectedTemplateId = null,
} = defineProps<{
  selectedTemplateId?: string | null;
}>();

const plannerState = useClassroomState();
const phoneStudentSheetOpen = ref(false);

const isSeatWorkspaceWithoutTemplate = computed(() => plannerState.template === null);
const phoneStudentCountLabel = computed(() => {
  const count = plannerState.unseatedStudents.length;
  return count === 1 ? "1 ej placerad" : `${count} ej placerade`;
});
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
const activeFixedSeatRules = computed(() => {
  const templateId = plannerState.template?.id ?? null;
  if (!templateId) {
    return [];
  }
  return plannerState.fixedSeatRules.filter((rule) => rule.template_id === templateId);
});
const smartRuleMarkersByStudentId = computed<Record<string, string[]>>(() => {
  return buildSmartRuleMarkersByStudentId(
    plannerState.seatingPreferences,
    plannerState.relationshipRules,
    activeFixedSeatRules.value,
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

function togglePhoneStudentSheet(): void {
  phoneStudentSheetOpen.value = !phoneStudentSheetOpen.value;
}

function setVisibleSeatingCanvasViewportSize(size: RoomViewportSize): void {
  if (size.width <= 0 || size.height <= 0) {
    return;
  }
  setSeatingCanvasViewportSize(size);
}
</script>

<template>
  <div class="flex min-h-0 flex-1 flex-col gap-3">
    <div
      v-if="plannerState.smartRuleHydrationStatus === 'error'"
      class="border border-warning/50 bg-warning/10 px-4 py-3 text-sm text-navy shadow-brutal-sm"
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
      class="planner-phone-seating-workspace"
      data-test="phone-seating-workspace"
    >
      <button
        type="button"
        class="planner-phone-seating-student-toggle"
        data-test="phone-seating-show-students"
        :aria-expanded="phoneStudentSheetOpen"
        @click="togglePhoneStudentSheet"
      >
        <span class="flex min-w-0 items-center gap-2">
          <IconStudents
            :size="17"
            class="shrink-0"
          />
          <span class="truncate">Elever</span>
        </span>
        <span class="flex shrink-0 items-center gap-2 text-xs text-navy/60">
          {{ phoneStudentCountLabel }}
          <IconArrow
            :size="15"
            :direction="phoneStudentSheetOpen ? 'up' : 'down'"
          />
        </span>
      </button>

      <div
        v-if="phoneStudentSheetOpen"
        class="planner-phone-seating-student-tray"
        data-test="phone-seating-student-sheet"
      >
        <PlannerStudentPool
          title="Ej placerade"
          :students="plannerState.unseatedStudents"
          :smart-rule-markers-by-student-id="smartRuleMarkersByStudentId"
          empty-label="Alla elever har fått plats"
          root-test-id="phone-seating-student-pool"
          @student-dragstart="onStudentDragStart($event.event, $event.studentId)"
          @pool-dragover="onDragOver"
          @pool-drop="onDropToPool"
        />
      </div>

      <RoomCanvas
        v-if="!isSeatWorkspaceWithoutTemplate"
        compact
        data-test="phone-seating-workspace-canvas"
        :scale-percent="seatingCanvasScalePercent"
        :scaled-surface-style="seatingCanvasScaledSurfaceStyle"
        :fixed-seat-rules="activeFixedSeatRules"
        :smart-rule-markers-by-student-id="smartRuleMarkersByStudentId"
        :surface-scale="seatingCanvasScale"
        @viewport-size="setVisibleSeatingCanvasViewportSize"
        @zoom-fit="resetSeatingCanvasZoom"
        @zoom-in="zoomInSeatingCanvas"
        @zoom-out="zoomOutSeatingCanvas"
      />
      <div
        v-else
        class="border border-dashed border-navy/30 bg-canvas px-4 py-6 text-center text-sm leading-relaxed text-navy/70"
      >
        Välj ett klassrum ovan för att börja placera sittplatser.
      </div>
    </div>

    <div
      :class="PLANNER_SEATING_LAYOUT_ROW_CLASS"
      data-test="seating-layout-lane"
    >
      <div
        :class="PLANNER_SEATING_STUDENT_POOL_LANE_CLASS"
        data-test="seating-student-pool-lane"
      >
        <PlannerStudentPool
          title="Ej placerade"
          :students="plannerState.unseatedStudents"
          :smart-rule-markers-by-student-id="smartRuleMarkersByStudentId"
          empty-label="Alla elever har fått plats"
          root-test-id="seating-student-pool"
          @student-dragstart="onStudentDragStart($event.event, $event.studentId)"
          @pool-dragover="onDragOver"
          @pool-drop="onDropToPool"
        />
      </div>

      <div
        :class="PLANNER_SEATING_WORKSPACE_LANE_CLASS"
        data-test="seating-workspace-lane"
      >
        <RoomCanvas
          v-if="!isSeatWorkspaceWithoutTemplate"
          data-test="seating-workspace"
          :scale-percent="seatingCanvasScalePercent"
          :scaled-surface-style="seatingCanvasScaledSurfaceStyle"
          :fixed-seat-rules="activeFixedSeatRules"
          :smart-rule-markers-by-student-id="smartRuleMarkersByStudentId"
          :surface-scale="seatingCanvasScale"
          @viewport-size="setVisibleSeatingCanvasViewportSize"
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
