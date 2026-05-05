<script setup lang="ts">
/**
 * Rules-map unplaced student grid.
 *
 * Purpose:
 *   Render the abstract roster/grid tray used below the rules map without
 *   coupling student-list layout to the room canvas implementation.
 *
 * Relationships:
 *   - consumed by `PlannerRulesMapCanvas.vue`
 *   - emits student selection back to the rules workspace state
 */

import type { Student } from "../classroomPlannerTypes";

withDefaults(defineProps<{
  students?: Student[];
  headingLabel: string;
  selectedCount?: number;
  studentCountLabel: string;
  isStudentSelected: (studentId: string) => boolean;
  selectionOrder: (studentId: string) => number | null;
  pendingFixedSeatStudentId?: string | null;
}>(), {
  students: () => [],
  selectedCount: 0,
  pendingFixedSeatStudentId: null,
});

const emit = defineEmits<{
  (e: "student-selected", studentId: string): void;
}>();
</script>

<template>
  <div
    v-if="students.length > 0"
    class="rules-unplaced-panel mt-3 border border-navy/20 bg-canvas px-3 py-3"
    data-test="rules-map-unplaced"
  >
    <div class="flex flex-wrap items-center justify-between gap-2 border-b border-navy/15 pb-2">
      <div class="space-y-1">
        <p
          class="text-[11px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/70"
          data-test="rules-map-surface-heading"
        >
          {{ headingLabel }}
        </p>
        <p
          class="text-xs font-medium text-navy/55"
          data-test="rules-map-unplaced-count"
        >
          {{ studentCountLabel }}
        </p>
      </div>
      <p
        v-if="selectedCount > 0"
        class="text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-action"
        data-test="rules-map-unplaced-selected-count"
      >
        {{ selectedCount }} valda
      </p>
    </div>
    <div
      class="rules-unplaced-grid mt-3"
      data-test="rules-map-unplaced-grid"
    >
      <button
        v-for="student in students"
        :key="student.id"
        type="button"
        class="rules-unplaced-student border text-left"
        :class="
          isStudentSelected(student.id)
            ? 'planner-choice-button-active-raised'
            : 'planner-choice-button-idle'
        "
        :data-test="`rules-unplaced-student-${student.id}`"
        :aria-pressed="isStudentSelected(student.id) ? 'true' : 'false'"
        @click="emit('student-selected', student.id)"
      >
        <span class="rules-unplaced-student-name">
          {{ student.display_name }}
        </span>
        <span
          v-if="selectionOrder(student.id)"
          class="rules-unplaced-student-order"
          :data-test="`rules-unplaced-student-order-${student.id}`"
        >
          {{ selectionOrder(student.id) }}
        </span>
        <span
          v-else-if="pendingFixedSeatStudentId === student.id"
          class="rules-unplaced-fixed-seat-preview"
          :data-test="`rules-unplaced-fixed-seat-preview-${student.id}`"
        >
          Fast plats
        </span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.rules-unplaced-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 0.65rem;
}

.rules-unplaced-student {
  display: flex;
  min-height: 3.25rem;
  width: 100%;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.75rem 0.875rem;
}

.rules-unplaced-student-name {
  min-width: 0;
  font-size: 0.875rem;
  font-weight: 600;
  line-height: 1.35;
  text-wrap: balance;
}

.rules-unplaced-student-order {
  display: inline-flex;
  min-height: 1.5rem;
  min-width: 1.5rem;
  align-items: center;
  justify-content: center;
  border: 1px solid currentColor;
  border-radius: 999px;
  flex-shrink: 0;
  font-size: 0.75rem;
  font-weight: 700;
  line-height: 1;
}

.rules-unplaced-fixed-seat-preview {
  display: inline-flex;
  min-height: 1.5rem;
  align-items: center;
  border: 1px dashed currentColor;
  flex-shrink: 0;
  padding: 0 0.45rem;
  font-size: 0.625rem;
  font-weight: 700;
  letter-spacing: var(--huleedu-tracking-label);
  line-height: 1;
  text-transform: uppercase;
}
</style>
