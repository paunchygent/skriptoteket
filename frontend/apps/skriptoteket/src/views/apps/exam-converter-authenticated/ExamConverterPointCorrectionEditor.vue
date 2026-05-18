<script setup lang="ts">
/**
 * Exam Converter point-correction editor.
 *
 * Domain purpose:
 *   Collect teacher-owned item point corrections for source-bound overlay
 *   submission without changing browser-local artifact readiness.
 *
 * Relationships:
 *   - Rendered by `ExamConverterQuestionReviewShell`.
 *   - Emits validated positive-integer point corrections to the authenticated
 *     Exam Converter host.
 *   - Projects returned `effective_point_correction` state through the parent
 *     review row instead of persisting local edits.
 */

import { computed, ref, watch } from "vue";
import { CheckCheck } from "lucide-vue-next";

import type { ExamConverterQuestionReviewRow } from "./digiexamIrReviewParser";

const props = defineProps<{
  question: ExamConverterQuestionReviewRow;
}>();

const emit = defineEmits<{
  applyPointCorrection: [question: ExamConverterQuestionReviewRow, maxScore: number];
}>();

const pointCorrectionDraft = ref("");

const pointCorrectionValue = computed(() => Number.parseInt(pointCorrectionDraft.value, 10));

const canApplyPointCorrection = computed(() => {
  const value = pointCorrectionValue.value;
  return (
    props.question.sourceItemFingerprint !== null &&
    Number.isInteger(value) &&
    value > 0 &&
    value !== props.question.pointsValue
  );
});

function pointDraftForQuestion(question: ExamConverterQuestionReviewRow): string {
  return question.pointsValue === null ? "" : String(question.pointsValue);
}

function applyPointCorrection(): void {
  if (!canApplyPointCorrection.value) return;
  emit("applyPointCorrection", props.question, pointCorrectionValue.value);
}

watch(
  () => [props.question.itemId, props.question.pointsValue],
  () => {
    pointCorrectionDraft.value = pointDraftForQuestion(props.question);
  },
  { immediate: true },
);
</script>

<template>
  <div
    class="mt-4 grid gap-2 border border-navy/20 bg-canvas p-3"
    data-test="exam-converter-point-correction-editor"
  >
    <label
      class="text-sm font-semibold leading-tight text-navy"
      for="exam-converter-point-correction-input"
    >
      Poäng
    </label>
    <div class="flex flex-wrap items-center gap-2">
      <input
        id="exam-converter-point-correction-input"
        v-model="pointCorrectionDraft"
        class="min-h-10 w-24 border border-navy/35 bg-panel px-3 text-sm font-semibold text-navy"
        data-test="exam-converter-point-correction-input"
        min="1"
        step="1"
        type="number"
      >
      <button
        type="button"
        class="btn-ghost inline-flex items-center gap-2 shadow-none"
        :disabled="!canApplyPointCorrection"
        data-test="exam-converter-apply-point-correction-action"
        title="Skickar poängändringen och uppdaterar frågan."
        @click="applyPointCorrection"
      >
        <CheckCheck
          class="h-4 w-4"
          aria-hidden="true"
        />
        Skicka ändring
      </button>
    </div>
  </div>
</template>
