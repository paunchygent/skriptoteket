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
import { Bot, CheckCircle2 } from "lucide-vue-next";

import type { ExamConverterQuestionReviewRow } from "./digiexamIrReviewParser";
import { isAiAnswerKeyProvenance } from "./digiexamIrQuestionReviewProjection";
import { effectiveGapAnswerDisplayEntries } from "./examConverterPersistedCorrectionDisplay";

const props = defineProps<{
  question: ExamConverterQuestionReviewRow;
}>();

const answerKeySummary = computed(() => {
  const answerKey = props.question.effectiveAnswerKey;
  if (!answerKey) return null;
  if (answerKey.correct_alternative_ids && answerKey.correct_alternative_ids.length > 0) {
    return answerKey.correct_alternative_ids.join(", ");
  }
  const gapAnswers = effectiveGapAnswerDisplayEntries(props.question);
  if (gapAnswers.length > 0) {
    return gapAnswers.map((gapAnswer) => gapAnswer.value).join(", ");
  }
  return null;
});

const gapAnswerEntries = computed(() => effectiveGapAnswerDisplayEntries(props.question));

const isAiAnswerKey = computed(() =>
  isAiAnswerKeyProvenance(props.question.currentAnswerKeyProvenance),
);

</script>

<template>
  <section
    v-if="answerKeySummary"
    class="grid gap-1 text-sm text-navy"
    data-test="exam-converter-effective-answer-key-summary"
  >
    <h5 class="inline-flex items-center gap-1.5 font-semibold leading-tight">
      <Bot
        v-if="isAiAnswerKey"
        class="h-4 w-4 text-success"
        data-test="exam-converter-effective-answer-key-ai-symbol"
        aria-hidden="true"
      />
      <CheckCircle2
        v-else
        class="h-4 w-4 text-success"
        data-test="exam-converter-effective-answer-key-teacher-symbol"
        aria-hidden="true"
      />
      <span>Facit</span>
    </h5>
    <p>
      {{ answerKeySummary }}
    </p>
  </section>
  <section
    v-if="gapAnswerEntries.length > 0"
    class="grid gap-2 text-sm text-navy"
  >
    <h5 class="font-semibold leading-tight">
      Luckor
    </h5>
    <div class="grid gap-1">
      <span
        v-for="gapAnswer in gapAnswerEntries"
        :key="gapAnswer.gapId"
        class="inline-flex w-fit border border-success/40 bg-success/10 px-2 py-1 text-xs font-semibold leading-tight text-success"
        :data-test="`exam-converter-effective-gap-answer-${gapAnswer.gapId}`"
      >
        {{ gapAnswer.label }}: {{ gapAnswer.value }}
      </span>
    </div>
  </section>
</template>
