<script setup lang="ts">
/**
 * Grouping workspace pane.
 *
 * This component now stays focused on the live grouping surface after ST-29-02
 * moved the toolbar into the shared planner shell. It composes the student
 * pool, any blocking local error surface, and the group board without
 * reintroducing full-width helper/status bands between the toolbar and the
 * work area.
 */

import { computed } from "vue";

import { buildSmartRuleMarkersByStudentId } from "../classroomPlannerSmartRulePresentation";
import {
  PLANNER_GROUPING_BOARD_LANE_CLASS,
  PLANNER_GROUPING_LAYOUT_ROW_CLASS,
  PLANNER_GROUPING_STUDENT_POOL_LANE_CLASS,
} from "../plannerWorkspaceLayout";
import GroupBoard from "./GroupBoard.vue";
import PlannerStudentPool from "./PlannerStudentPool.vue";
import { useClassroomState } from "../useClassroomState";

const state = useClassroomState();
const smartRuleMarkersByStudentId = computed<Record<string, string[]>>(() => {
  return buildSmartRuleMarkersByStudentId(
    state.seatingPreferences,
    state.relationshipRules,
  );
});

function onDragStart(event: DragEvent, studentId: string): void {
  if (state.isWorkspaceBusy) {
    return;
  }
  if (event.dataTransfer) {
    event.dataTransfer.setData("studentId", studentId);
    event.dataTransfer.effectAllowed = "move";
  }
}

function onDropToPool(event: DragEvent): void {
  if (state.isWorkspaceBusy) {
    return;
  }
  event.preventDefault();
  const studentId = event.dataTransfer?.getData("studentId");
  if (studentId) {
    state.removeStudentFromGroup(studentId);
  }
}

function onDragOver(event: DragEvent): void {
  if (state.isWorkspaceBusy) {
    return;
  }
  event.preventDefault();
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = "move";
  }
}
</script>

<template>
  <div class="flex min-h-0 flex-1 flex-col gap-3">
    <div
      v-if="state.smartRuleHydrationStatus === 'error'"
      class="border border-amber-300/80 bg-amber-50 px-4 py-3 text-sm text-amber-900 shadow-brutal-sm"
      data-test="grouping-smart-hydration-error"
    >
      <div class="flex flex-wrap items-center justify-between gap-3">
        <p>
          {{ state.smartRuleHydrationMessage }}
        </p>
        <button
          type="button"
          class="btn-ghost planner-btn-alert planner-btn-ghost-sm"
          data-test="grouping-smart-retry-hydration"
          @click="void state.retrySmartRuleHydration()"
        >
          Försök igen
        </button>
      </div>
    </div>

    <div
      :class="PLANNER_GROUPING_LAYOUT_ROW_CLASS"
      data-test="grouping-layout-lane"
    >
      <div
        :class="PLANNER_GROUPING_STUDENT_POOL_LANE_CLASS"
        data-test="grouping-student-pool-lane"
      >
        <PlannerStudentPool
          title="Ej grupperade"
          :students="state.ungroupedStudents"
          :smart-rule-markers-by-student-id="smartRuleMarkersByStudentId"
          :disabled="state.isWorkspaceBusy"
          empty-label="Alla elever ligger i grupp"
          root-test-id="grouping-student-pool"
          @student-dragstart="onDragStart($event.event, $event.studentId)"
          @pool-dragover="onDragOver"
          @pool-drop="onDropToPool"
        />
      </div>

      <div
        :class="PLANNER_GROUPING_BOARD_LANE_CLASS"
        data-test="grouping-board-lane"
      >
        <GroupBoard
          :smart-rule-markers-by-student-id="smartRuleMarkersByStudentId"
        />
      </div>
    </div>
  </div>
</template>
