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
import {
  effectiveGapAnswerEntries,
  isEffectiveChoiceAlternative,
} from "./examConverterPersistedCorrectionDisplay";

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

const gapAnswerEntries = computed(() => effectiveGapAnswerEntries(props.question));

const hasChoiceAnswerKey = computed(
  () => (props.question.effectiveAnswerKey?.correct_alternative_ids?.length ?? 0) > 0,
);
</script>

<template>
  <div
    v-if="answerKeySummary"
    class="grid grid-cols-[7rem_minmax(0,1fr)] gap-3"
    data-test="exam-converter-effective-answer-key-summary"
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
  <div
    v-if="gapAnswerEntries.length > 0"
    class="grid grid-cols-[7rem_minmax(0,1fr)] gap-3"
  >
    <dt class="text-navy">
      Luckor
    </dt>
    <dd class="grid gap-1 text-navy">
      <span
        v-for="[gapId, value] in gapAnswerEntries"
        :key="gapId"
        class="inline-flex w-fit border border-success/40 bg-success/10 px-2 py-1 text-xs font-semibold leading-tight text-success"
        :data-test="`exam-converter-effective-gap-answer-${gapId}`"
      >
        {{ gapId }}: {{ value }}
      </span>
    </dd>
  </div>
  <div
    v-if="hasChoiceAnswerKey"
    class="grid grid-cols-[7rem_minmax(0,1fr)] gap-3"
  >
    <dt class="text-navy">
      Alternativ
    </dt>
    <dd>
      <ol
        class="grid gap-2 text-sm text-navy"
        data-test="exam-converter-effective-choice-answer-key"
      >
        <li
          v-for="alternative in question.alternatives"
          :key="alternative.id"
          class="grid grid-cols-[2rem_minmax(0,1fr)] gap-3 border border-navy/15 bg-panel px-2 py-2"
          :data-test="`exam-converter-effective-choice-${alternative.id}`"
        >
          <span
            class="inline-grid h-7 w-7 place-items-center border text-xs font-semibold leading-none"
            :class="isEffectiveChoiceAlternative({ question, alternativeId: alternative.id }) ? 'border-success bg-success text-panel' : 'border-navy/25 bg-panel text-navy'"
            :data-test="`exam-converter-effective-choice-ordinal-${alternative.id}`"
          >
            {{ alternative.id }}
          </span>
          <span class="leading-relaxed">
            {{ alternative.text }}
          </span>
        </li>
      </ol>
    </dd>
  </div>
</template>
