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

import { computed, ref, watch } from "vue";

import { buildSmartRuleMarkersByStudentId } from "../classroomPlannerSmartRulePresentation";
import type { DraftGroup } from "../classroomPlannerTypes";
import {
  PLANNER_GROUPING_BOARD_LANE_CLASS,
  PLANNER_GROUPING_LAYOUT_ROW_CLASS,
  PLANNER_GROUPING_STUDENT_POOL_LANE_CLASS,
} from "../plannerWorkspaceLayout";
import GroupBoard from "./GroupBoard.vue";
import GroupCard from "./GroupCard.vue";
import PlannerStudentPool from "./PlannerStudentPool.vue";
import { useClassroomState } from "../useClassroomState";

const state = useClassroomState();
const mobileActiveGroupId = ref<string | null>(null);
const smartRuleMarkersByStudentId = computed<Record<string, string[]>>(() => {
  return buildSmartRuleMarkersByStudentId(
    state.seatingPreferences,
    state.relationshipRules,
  );
});
const orderedGroups = computed(() => [...state.groups].sort((left, right) => left.sort_order - right.sort_order));
const mobileActiveGroup = computed<DraftGroup | null>(() => {
  return orderedGroups.value.find((group) => group.id === mobileActiveGroupId.value) ?? null;
});
const mobileActiveGroupIndex = computed(() => {
  if (!mobileActiveGroup.value) {
    return -1;
  }
  return orderedGroups.value.findIndex((group) => group.id === mobileActiveGroup.value?.id);
});

watch(orderedGroups, (groups) => {
  if (groups.length === 0) {
    mobileActiveGroupId.value = null;
    return;
  }
  if (!mobileActiveGroupId.value || !groups.some((group) => group.id === mobileActiveGroupId.value)) {
    mobileActiveGroupId.value = groups[0]?.id ?? null;
  }
}, { immediate: true });

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

function selectMobileGroup(groupId: string): void {
  mobileActiveGroupId.value = groupId;
}
</script>

<template>
  <div class="flex min-h-0 flex-1 flex-col gap-3">
    <div
      v-if="state.smartRuleHydrationStatus === 'error'"
      class="border border-warning/50 bg-warning/10 px-4 py-3 text-sm text-navy shadow-brutal-sm"
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
      class="planner-phone-grouping-workspace"
      data-test="phone-grouping-workspace"
    >
      <div
        class="planner-phone-tab-strip"
        aria-label="Välj grupp"
      >
        <button
          v-for="group in orderedGroups"
          :key="group.id"
          type="button"
          class="planner-phone-tab"
          :class="mobileActiveGroup?.id === group.id ? 'planner-phone-tab-active' : ''"
          :data-test="`phone-grouping-tab-${group.id}`"
          @click="selectMobileGroup(group.id)"
        >
          {{ group.name }}
        </button>
      </div>

      <div class="planner-phone-grouping-target">
        <GroupCard
          v-if="mobileActiveGroup"
          :group="mobileActiveGroup"
          :students="state.studentsByGroupId[mobileActiveGroup.id] ?? []"
          :can-move-up="mobileActiveGroupIndex > 0"
          :can-move-down="mobileActiveGroupIndex >= 0 && mobileActiveGroupIndex < orderedGroups.length - 1"
          :smart-rule-markers-by-student-id="smartRuleMarkersByStudentId"
          :disabled="state.isWorkspaceBusy"
          data-test="phone-grouping-active-card"
          @student-dropped="state.assignStudentToGroup"
          @student-removed="state.removeStudentFromGroup"
          @group-renamed="state.renameGroup"
          @group-moved="state.moveGroup"
          @group-removed="state.removeGroup"
        />
        <div
          v-else
          class="planner-phone-drop-target"
          data-test="phone-grouping-target-placeholder"
        >
          Förbereder grupper
          <span>Gruppytan visas här när utkastet är klart.</span>
        </div>
      </div>

      <PlannerStudentPool
        title="Ej grupperade"
        :students="state.ungroupedStudents"
        :smart-rule-markers-by-student-id="smartRuleMarkersByStudentId"
        :disabled="state.isWorkspaceBusy"
        empty-label="Alla elever ligger i grupp"
        root-test-id="phone-grouping-student-pool"
        @student-dragstart="onDragStart($event.event, $event.studentId)"
        @pool-dragover="onDragOver"
        @pool-drop="onDropToPool"
      />
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
