<script setup lang="ts">
/**
 * Exam Converter effective answer-key summary.
 *
 * Domain purpose:
 *   Show teacher-facing answer-key values only after Exam Converter has returned
 *   them in effective IR.
 *
 * Relationships:
 *   - Rendered by `ExamConverterQuestionReviewShell`.
 *   - Reads projected `effective_answer_key` state without consulting local
 *     edit drafts or advisory candidate metadata.
 */

import { computed } from "vue";

import { IconCheck } from "../../../components/icons";
import type { ExamConverterQuestionReviewRow } from "./digiexamIrReviewParser";
import { effectiveGapAnswerDisplayEntries } from "./examConverterPersistedCorrectionDisplay";

const props = defineProps<{
  question: ExamConverterQuestionReviewRow;
}>();

const choiceAnswerEntries = computed(() => {
  const answerKey = props.question.effectiveAnswerKey;
  const correctAlternativeIds = answerKey?.correct_alternative_ids ?? [];
  const alternativesById = new Map(
    props.question.alternatives.map((alternative) => [
      Number.parseInt(alternative.id, 10),
      alternative,
    ]),
  );
  return correctAlternativeIds.map((id) => {
    const alternative = alternativesById.get(id);
    return {
      id,
      label: id.toLocaleString("sv-SE"),
      text: alternative?.text ?? null,
    };
  });
});

const gapAnswerEntries = computed(() => effectiveGapAnswerDisplayEntries(props.question));

const gapAnswerSummary = computed(() => {
  if (gapAnswerEntries.value.length === 0) return null;
  return gapAnswerEntries.value.map((gapAnswer) => gapAnswer.value).join(", ");
});

const hasAnswerKeySummary = computed(
  () => choiceAnswerEntries.value.length > 0 || gapAnswerSummary.value !== null,
);

</script>

<template>
  <section
    v-if="hasAnswerKeySummary"
    class="grid gap-1 text-sm text-navy"
    data-test="exam-converter-effective-answer-key-summary"
  >
    <h5 class="inline-flex items-center gap-1.5 font-semibold leading-tight">
      <IconCheck
        :size="16"
        class="h-4 w-4 text-success"
        data-test="exam-converter-effective-answer-key-teacher-symbol"
        aria-hidden="true"
      />
      <span>Facit</span>
    </h5>
    <ol
      v-if="choiceAnswerEntries.length > 0"
      class="mt-1 grid gap-2"
      data-test="exam-converter-effective-answer-key-choices"
    >
      <li
        v-for="entry in choiceAnswerEntries"
        :key="entry.id"
        class="grid grid-cols-[2rem_minmax(0,1fr)] gap-3"
        :data-test="`exam-converter-effective-answer-key-choice-${entry.id}`"
      >
        <span
          class="inline-grid h-7 w-7 place-items-center border border-success bg-success text-xs font-semibold leading-none text-panel"
        >
          {{ entry.label }}
        </span>
        <span class="leading-relaxed">
          {{ entry.text ?? `Alternativ ${entry.label}` }}
        </span>
      </li>
    </ol>
    <p v-else-if="gapAnswerSummary">
      {{ gapAnswerSummary }}
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
