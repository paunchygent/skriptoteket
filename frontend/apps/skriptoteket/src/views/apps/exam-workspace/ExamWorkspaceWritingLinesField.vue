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
 *   - Rendered by `ExamWorkspaceQuestionEditor` for a free-text item that
 *     carries a writing-line count, directly above its criteria.
 *   - Receives the count from the item; the editor renders no field when the
 *     item has none.
 *   - Emits the value; `useExamWorkspaceItemEdits` (`updateItemWritingLines`)
 *     and `useExamWorkspaceDocumentFields` (`applyWritingLinesToAllFreeText`)
 *     own the state.
 *   - Reads the house bounds from `examWorkspaceWritingLines`.
 */

import { computed, useId } from "vue";

import { MAX_WRITING_LINES, MIN_WRITING_LINES } from "./examWorkspaceWritingLines";

const props = defineProps<{
  disabled?: boolean;
  /** The question's writing-line count; the editor renders the field only when the item has one. */
  lines: number;
  /** True when every free-text question in the exam already has this count. */
  allFreeTextMatch: boolean;
  /**
   * The id of the element that states why the controls are locked, when the
   * question is locked for a reason the teacher cannot read from the buttons
   * themselves; null or omitted when no such reason applies.
   */
  lockedReasonId?: string | null;
}>();

const emit = defineEmits<{
  update: [lines: number];
  applyToAll: [lines: number];
}>();

/** The question's writing lines, passed in by the editor. */
const labelId = useId();
const label = computed(() => (props.lines === 1 ? "1 rad" : `${props.lines} rader`));
const atMin = computed(() => props.lines <= MIN_WRITING_LINES);
const atMax = computed(() => props.lines >= MAX_WRITING_LINES);
/** The bound each stepper button is stopped by, or undefined while it can move. */
const minReason = computed(() => (atMin.value ? `Minst ${MIN_WRITING_LINES} rad` : undefined));
const maxReason = computed(() => (atMax.value ? `Högst ${MAX_WRITING_LINES} rader` : undefined));
/** Why apply-to-all is stopped, or undefined while it has work to do. */
const applyAllReason = computed(() =>
  props.allFreeTextMatch ? `Alla fritextfrågor har redan ${props.lines} rader` : undefined,
);
/** The lock notice the buttons point at, only while the whole field is locked. */
const lockReasonId = computed(() => (props.disabled && props.lockedReasonId ? props.lockedReasonId : undefined));

function step(delta: -1 | 1): void {
  emit("update", props.lines + delta);
}

function applyToAll(): void {
  emit("applyToAll", props.lines);
}
</script>

<template>
  <div
    class="xw-answer-row"
    role="group"
    :aria-labelledby="labelId"
    data-test="exam-workspace-writing-lines"
  >
    <div
      :id="labelId"
      class="xw-answer-label"
    >
      Skrivyta
    </div>
    <div class="xw-answer-controls">
      <button
        type="button"
        class="inline-flex h-10 w-10 items-center justify-center border border-navy/35 bg-panel text-lg font-semibold text-navy hover:bg-canvas disabled:opacity-50"
        :disabled="disabled || atMin"
        :title="minReason"
        :aria-describedby="lockReasonId"
        aria-label="Färre rader"
        data-test="exam-workspace-writing-lines-minus"
        @click="step(-1)"
      >
        −
      </button>
      <span data-test="exam-workspace-writing-lines-count">{{ label }}</span>
      <button
        type="button"
        class="inline-flex h-10 w-10 items-center justify-center border border-navy/35 bg-panel text-lg font-semibold text-navy hover:bg-canvas disabled:opacity-50"
        :disabled="disabled || atMax"
        :title="maxReason"
        :aria-describedby="lockReasonId"
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
        :title="applyAllReason"
        :aria-describedby="lockReasonId"
        data-test="exam-workspace-writing-lines-apply-all"
        @click="applyToAll"
      >
        Använd för alla fritextfrågor
      </button>
    </div>
  </div>
</template>
