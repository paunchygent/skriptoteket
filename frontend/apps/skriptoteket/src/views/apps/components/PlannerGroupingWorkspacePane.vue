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

import GroupBoard from "./GroupBoard.vue";
import PlannerStudentPool from "./PlannerStudentPool.vue";
import { useClassroomState } from "../useClassroomState";

withDefaults(
  defineProps<{
    selectedStudentId?: string | null;
  }>(),
  {
    selectedStudentId: null,
  },
);

const emit = defineEmits<{
  (e: "student-selected", studentId: string): void;
}>();

const state = useClassroomState();
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
  <div class="flex flex-col gap-3">
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

    <div class="grid gap-3 xl:grid-cols-[240px_minmax(0,1fr)] xl:items-stretch">
      <PlannerStudentPool
        title="Ej grupperade"
        :students="state.ungroupedStudents"
        :selected-student-id="selectedStudentId"
        :disabled="state.isWorkspaceBusy"
        empty-label="Alla elever ligger i grupp"
        root-test-id="grouping-student-pool"
        @student-selected="emit('student-selected', $event)"
        @student-dragstart="onDragStart($event.event, $event.studentId)"
        @pool-dragover="onDragOver"
        @pool-drop="onDropToPool"
      />

      <GroupBoard
        :selected-student-id="selectedStudentId"
        @student-selected="emit('student-selected', $event)"
      />
    </div>
  </div>
</template>
