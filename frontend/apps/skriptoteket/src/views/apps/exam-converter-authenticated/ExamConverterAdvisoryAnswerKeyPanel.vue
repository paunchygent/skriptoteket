<script setup lang="ts">
/**
 * Exam Converter advisory answer-key review panel.
 *
 * Domain purpose:
 *   Present the teacher's explicit choice for a producer-backed advisory
 *   answer-key candidate before any manual answer-key editing surface opens.
 *
 * Relationships:
 *   - Rendered by `ExamConverterQuestionReviewShell` for compact
 *     `review_required` advisory rows.
 *   - Emits the existing bounded manual answer-key correction shape so
 *     local replay remains the only review-state authority.
 *   - Keeps advisory provenance as selected-detail context, never as list,
 *     completion, or file-readiness truth.
 */

import { computed } from "vue";

import { IconAi } from "../../../components/icons";
import type { ExamConverterQuestionReviewRow } from "./digiexamIrReviewParser";

const props = defineProps<{ question: ExamConverterQuestionReviewRow }>();

const candidatePayload = computed(() => props.question.llmCandidate?.answerPayload ?? null);

const candidateChoiceEntries = computed(() => {
  const payload = candidatePayload.value;
  if (payload?.kind !== "choice") return [];
  const selectedIds = new Set(payload.correctAlternativeIds);
  return props.question.alternatives.filter((alternative) =>
    selectedIds.has(Number.parseInt(alternative.id, 10)),
  );
});

const candidateGapEntries = computed(() => {
  const payload = candidatePayload.value;
  if (payload?.kind !== "gap_fill") return [];
  const labelsByGapId = new Map(props.question.gaps.map((gap) => [gap.id, gap.label]));
  return payload.gapAnswers.map((gapAnswer) => ({
    gapId: gapAnswer.gapId,
    label: labelsByGapId.get(gapAnswer.gapId) ?? gapAnswer.gapId,
    value: gapAnswer.acceptedValues.join(", "),
  }));
});

</script>

<template>
  <section
    v-if="candidatePayload"
    class="grid gap-3 border border-action/35 bg-action/5 p-3 text-sm text-navy"
    data-test="exam-converter-selected-question-ai-suggestion"
  >
    <div class="flex items-start gap-2">
      <IconAi
        :size="18"
        class="mt-0.5 h-4 w-4 shrink-0 text-success"
        aria-hidden="true"
      />
      <div class="grid min-w-0 gap-1">
        <h5 class="font-semibold leading-tight">
          Föreslaget facit
        </h5>
      </div>
    </div>

    <div
      class="grid gap-2"
      data-test="exam-converter-previous-answer-key-suggestion"
    >
      <ol
        v-if="candidateChoiceEntries.length > 0"
        class="grid gap-2 md:grid-cols-2"
      >
        <li
          v-for="entry in candidateChoiceEntries"
          :key="entry.id"
          class="grid min-w-0 grid-cols-[2rem_minmax(0,1fr)] gap-3 border border-success/40 bg-success/10 px-2 py-2"
          :data-test="`exam-converter-advisory-choice-${entry.id}`"
        >
          <span class="inline-grid h-7 w-7 place-items-center border border-success bg-success text-xs font-semibold leading-none text-panel">
            {{ entry.id }}
          </span>
          <span class="leading-relaxed">
            {{ entry.text }}
          </span>
        </li>
      </ol>
      <div
        v-else
        class="grid gap-2 md:grid-cols-2"
      >
        <span
          v-for="entry in candidateGapEntries"
          :key="entry.gapId"
          class="inline-flex min-w-0 border border-success/40 bg-success/10 px-2 py-2 text-xs font-semibold leading-tight text-success"
          :data-test="`exam-converter-advisory-gap-${entry.gapId}`"
        >
          {{ entry.label }}: {{ entry.value }}
        </span>
      </div>
    </div>
  </section>
</template>
