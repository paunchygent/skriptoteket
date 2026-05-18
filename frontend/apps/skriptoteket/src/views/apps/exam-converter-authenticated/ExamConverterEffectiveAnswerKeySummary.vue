<script setup lang="ts">
/**
 * Exam Converter effective answer-key summary.
 *
 * Domain purpose:
 *   Show teacher-facing answer-key values only after Sir Convert has returned
 *   them in effective IR.
 *
 * Relationships:
 *   - Rendered by `ExamConverterQuestionReviewShell`.
 *   - Reads projected `effective_answer_key` state without consulting local
 *     edit drafts or advisory candidate metadata.
 */

import { computed } from "vue";

import type { ExamConverterQuestionReviewRow } from "./digiexamIrReviewParser";

const props = defineProps<{
  question: ExamConverterQuestionReviewRow;
}>();

const answerKeySummary = computed(() => {
  const answerKey = props.question.effectiveAnswerKey;
  if (!answerKey) return null;
  if (answerKey.correct_alternative_ids && answerKey.correct_alternative_ids.length > 0) {
    return answerKey.correct_alternative_ids.join(", ");
  }
  if (answerKey.correct_gap_answers && answerKey.correct_gap_answers.length > 0) {
    return answerKey.correct_gap_answers
      .flatMap((gapAnswer) => Object.entries(gapAnswer))
      .map(([gapId, value]) => `${gapId}: ${value}`)
      .join(", ");
  }
  return null;
});
</script>

<template>
  <div
    v-if="answerKeySummary"
    class="grid grid-cols-[7rem_minmax(0,1fr)] gap-3"
  >
    <dt class="text-navy">
      Facit
    </dt>
    <dd class="text-navy">
      {{ answerKeySummary }}
      <span class="ml-2 text-xs font-semibold uppercase tracking-[0.08em] text-success">
        Ändrat
      </span>
    </dd>
  </div>
</template>
