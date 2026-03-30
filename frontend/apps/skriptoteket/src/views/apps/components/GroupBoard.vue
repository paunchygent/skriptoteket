<script setup lang="ts">
/**
 * Group planning board.
 *
 * This component now renders only the ordered grouping buckets for the active
 * draft. The surrounding student pool and task toolbar live in the grouping
 * workspace pane so the board can stay focused on group-card composition.
 */

import { computed } from "vue";

import GroupCard from "./GroupCard.vue";
import { useClassroomState } from "../useClassroomState";

const props = defineProps<{
  selectedStudentId?: string | null;
  smartRuleMarkersByStudentId?: Record<string, string[]>;
}>();

const emit = defineEmits<{
  (e: "student-selected", studentId: string): void;
}>();

const state = useClassroomState();
const orderedGroups = computed(() => [...state.groups].sort((left, right) => left.sort_order - right.sort_order));
</script>

<template>
  <div class="grid items-start gap-3 md:grid-cols-2 2xl:grid-cols-3">
    <GroupCard
      v-for="(group, index) in orderedGroups"
      :key="group.id"
      :group="group"
      :students="state.studentsByGroupId[group.id] ?? []"
      :can-move-up="index > 0"
      :can-move-down="index < orderedGroups.length - 1"
      :selected-student-id="props.selectedStudentId"
      :smart-rule-markers-by-student-id="props.smartRuleMarkersByStudentId"
      :disabled="state.isWorkspaceBusy"
      @student-dropped="state.assignStudentToGroup"
      @student-removed="state.removeStudentFromGroup"
      @group-renamed="state.renameGroup"
      @group-moved="state.moveGroup"
      @group-removed="state.removeGroup"
      @student-selected="emit('student-selected', $event)"
    />
  </div>
</template>
