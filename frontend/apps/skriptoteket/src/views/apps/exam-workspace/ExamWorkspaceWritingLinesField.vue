<script setup lang="ts">
/**
 * Exam workspace Skrivyta field.
 *
 * Domain purpose:
 *   Size a free-text question's printed writing area (W4): the current count as
 *   "Skrivyta: N rader", a − / + stepper that emits the next count, and
 *   "Använd för alla fritextfrågor" which emits the current count for every
 *   free-text question. The count is clamped to the house range by the pure
 *   transition the command applies.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceQuestionEditor` for free-text items only,
 *     directly above its criteria.
 *   - Emits the value; `useExamWorkspaceItemEdits` (`updateItemWritingLines`)
 *     and `useExamWorkspaceDocumentFields` (`applyWritingLinesToAllFreeText`)
 *     own the state.
 *   - Reads the house bounds from `examWorkspaceWritingLines`.
 */

import { computed } from "vue";

import type { NativeExamItem } from "../../../api/examWorkspace";
import {
  DEFAULT_WRITING_LINES,
  MAX_WRITING_LINES,
  MIN_WRITING_LINES,
} from "./examWorkspaceWritingLines";

const props = defineProps<{
  disabled?: boolean;
  item: NativeExamItem;
  /** True when every free-text question in the exam already has this count. */
  allFreeTextMatch: boolean;
}>();

const emit = defineEmits<{
  update: [lines: number];
  applyToAll: [lines: number];
}>();

/** The question's writing lines; a free-text question's area is never unset. */
const lines = computed(() => props.item.writing_lines ?? DEFAULT_WRITING_LINES);
const label = computed(() => (lines.value === 1 ? "1 rad" : `${lines.value} rader`));
const atMin = computed(() => lines.value <= MIN_WRITING_LINES);
const atMax = computed(() => lines.value >= MAX_WRITING_LINES);

function step(delta: -1 | 1): void {
  emit("update", lines.value + delta);
}

function applyToAll(): void {
  emit("applyToAll", lines.value);
}
</script>

<template>
  <fieldset
    class="grid gap-2"
    data-test="exam-workspace-writing-lines"
  >
    <legend class="mb-2 text-xs font-semibold text-navy/80">
      Skrivyta: {{ label }}
    </legend>
    <div class="flex items-center gap-2">
      <button
        type="button"
        class="inline-flex h-10 w-10 items-center justify-center border border-navy/35 bg-panel text-lg font-semibold text-navy hover:bg-canvas disabled:opacity-50"
        :disabled="disabled || atMin"
        aria-label="Färre rader"
        data-test="exam-workspace-writing-lines-minus"
        @click="step(-1)"
      >
        −
      </button>
      <button
        type="button"
        class="inline-flex h-10 w-10 items-center justify-center border border-navy/35 bg-panel text-lg font-semibold text-navy hover:bg-canvas disabled:opacity-50"
        :disabled="disabled || atMax"
        aria-label="Fler rader"
        data-test="exam-workspace-writing-lines-plus"
        @click="step(1)"
      >
        +
      </button>
      <button
        type="button"
        class="inline-flex min-h-10 items-center gap-2 border border-navy/35 bg-panel px-3 text-sm font-semibold text-navy hover:bg-canvas disabled:opacity-50"
        :disabled="disabled || allFreeTextMatch"
        data-test="exam-workspace-writing-lines-apply-all"
        @click="applyToAll"
      >
        Använd för alla fritextfrågor
      </button>
    </div>
  </fieldset>
</template>
