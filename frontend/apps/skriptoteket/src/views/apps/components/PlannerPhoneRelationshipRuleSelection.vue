<script setup lang="ts">
/**
 * Phone relationship-rule selection panel.
 *
 * Purpose:
 *   Renders the compact selected-student target used by phone relationship
 *   rules without owning planner state or persistence.
 *
 * Relationships:
 *   - rendered by `PlannerRulesWorkspacePane.vue` for non-fixed-seat tools
 *   - emits selection mutation intents back to the planner state owner
 */

import { IconX } from "../../../components/icons";

defineProps<{
  students: Array<{ id: string; name: string }>;
}>();

const emit = defineEmits<{
  (e: "clear-selection"): void;
  (e: "remove-student", studentId: string): void;
  (e: "selection-dragover", event: DragEvent): void;
  (e: "selection-drop", event: DragEvent): void;
}>();
</script>

<template>
  <div
    class="planner-phone-rules-selection"
    data-test="phone-rules-selection"
    @dragover="emit('selection-dragover', $event)"
    @drop="emit('selection-drop', $event)"
  >
    <div class="flex items-center justify-between gap-3">
      <h3 class="text-sm font-semibold text-navy">
        Valda elever ({{ students.length }})
      </h3>
      <button
        type="button"
        class="planner-phone-link-button"
        data-test="phone-rules-clear-selection"
        :disabled="students.length === 0"
        @click="emit('clear-selection')"
      >
        Rensa
      </button>
    </div>
    <div
      v-if="students.length > 0"
      class="mt-2 grid gap-1.5"
    >
      <div
        v-for="student in students"
        :key="student.id"
        class="planner-phone-selected-student-row"
        data-test="phone-rules-selected-student"
      >
        <span class="truncate">{{ student.name }}</span>
        <button
          type="button"
          class="planner-row-remove-button"
          :aria-label="`Ta bort ${student.name} från regeln`"
          @click="emit('remove-student', student.id)"
        >
          <IconX :size="14" />
        </button>
      </div>
    </div>
  </div>
</template>
