<script setup lang="ts">
/**
 * Shared planner student-pool sidebar.
 *
 * This component renders the unassigned-student list used by both grouping and
 * seating panes. It stays presentational and emits drag/click events so the
 * task-specific workspace containers keep ownership of planner mutations.
 */

import type { Student } from "../classroomPlannerTypes";

withDefaults(
  defineProps<{
    title: string;
    students: Student[];
    selectedStudentId?: string | null;
    selectedStudentIds?: string[];
    smartRuleMarkersByStudentId?: Record<string, string[]>;
    emptyLabel: string;
    disabled?: boolean;
    rootTestId?: string;
    emptyTestId?: string;
  }>(),
  {
    selectedStudentId: null,
    selectedStudentIds: () => [],
    smartRuleMarkersByStudentId: () => ({}),
    disabled: false,
    rootTestId: undefined,
    emptyTestId: undefined,
  },
);

const emit = defineEmits<{
  (e: "student-selected", studentId: string): void;
  (e: "student-dragstart", payload: { event: DragEvent; studentId: string }): void;
  (e: "pool-dragover", event: DragEvent): void;
  (e: "pool-drop", event: DragEvent): void;
}>();
</script>

<template>
  <aside
    class="flex flex-col border border-navy bg-white p-3 shadow-brutal-sm xl:sticky xl:top-4 xl:max-h-[calc(100svh-6rem)]"
    :data-test="rootTestId"
    :aria-label="title"
    @dragover="emit('pool-dragover', $event)"
    @drop="emit('pool-drop', $event)"
  >
    <div class="flex items-end justify-between gap-3 border-b border-navy/20 pb-2">
      <div>
        <h3 class="font-serif text-lg text-navy">
          {{ title }}
        </h3>
      </div>
      <span class="border border-navy bg-canvas px-2 py-1 text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/70">
        {{ students.length }}
      </span>
    </div>

    <div class="mt-3 flex flex-1 flex-col gap-1.5 overflow-y-auto">
      <button
        v-for="student in students"
        :key="student.id"
        type="button"
        class="flex items-start justify-between gap-2.5 border px-3 py-1.5 text-left transition-colors"
        :class="selectedStudentId === student.id || selectedStudentIds.includes(student.id) ? 'planner-choice-button-active' : 'planner-choice-button-strong'"
        :disabled="disabled"
        :draggable="!disabled"
        @click="emit('student-selected', student.id)"
        @dragstart="emit('student-dragstart', { event: $event, studentId: student.id })"
      >
        <div class="min-w-0">
          <div class="truncate text-sm font-semibold">
            {{ student.display_name }}
          </div>
        </div>
        <div
          v-if="(smartRuleMarkersByStudentId[student.id] ?? []).length > 0"
          class="flex flex-wrap justify-end gap-1"
          :data-test="`student-pool-markers-${student.id}`"
        >
          <span
            v-for="marker in smartRuleMarkersByStudentId[student.id]"
            :key="marker"
            class="border border-navy/20 bg-canvas px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/70"
          >
            {{ marker }}
          </span>
        </div>
      </button>

      <div
        v-if="students.length === 0"
        class="flex flex-1 items-center justify-center border border-dashed border-navy/30 bg-canvas px-4 py-4 text-center text-[11px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/40"
        :data-test="emptyTestId"
      >
        {{ emptyLabel }}
      </div>
    </div>
  </aside>
</template>
