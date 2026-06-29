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
 *     Sir Convert replay remains the only review-state authority.
 *   - Keeps advisory provenance as selected-detail context, never as list,
 *     completion, or file-readiness truth.
 */

import { computed } from "vue";

import { IconAi, IconEdit } from "../../../components/icons";
import type {
  ExamConverterManualAnswerKeyCorrection,
} from "./digiexamTeacherCorrectionOverlay";
import type { ExamConverterQuestionReviewRow } from "./digiexamIrReviewParser";

const props = defineProps<{
  disabled: boolean;
  question: ExamConverterQuestionReviewRow;
}>();

const emit = defineEmits<{
  acceptAdvisoryAnswerKey: [
    question: ExamConverterQuestionReviewRow,
    answerKey: ExamConverterManualAnswerKeyCorrection,
  ];
  editAdvisoryAnswerKey: [question: ExamConverterQuestionReviewRow];
}>();

const candidatePayload = computed(() => props.question.llmCandidate?.answerPayload ?? null);

const advisoryAnswerKey = computed<ExamConverterManualAnswerKeyCorrection | null>(() => {
  const payload = candidatePayload.value;
  if (payload?.kind === "choice") {
    return {
      correctAlternativeIds: [...payload.correctAlternativeIds],
      kind: "choice",
    };
  }
  if (payload?.kind === "gap_fill") {
    return {
      gapAnswers: payload.gapAnswers.map((gapAnswer) => ({
        acceptedValues: [...gapAnswer.acceptedValues],
        gapId: gapAnswer.gapId,
      })),
      kind: "gap_fill",
    };
  }
  return null;
});

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

function acceptAdvisoryAnswerKey(): void {
  if (props.disabled || props.question.sourceItemFingerprint === null || !advisoryAnswerKey.value) {
    return;
  }
  emit("acceptAdvisoryAnswerKey", props.question, advisoryAnswerKey.value);
}
</script>

<template>
  <section
    v-if="advisoryAnswerKey"
    class="mt-4 grid gap-3 border border-action/35 bg-action/5 p-3 text-sm text-navy"
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
          Granska facit
        </h5>
        <p class="leading-relaxed text-navy/75">
          Acceptera förslaget oförändrat eller ändra innan du sparar ett eget facit.
        </p>
      </div>
    </div>

    <div
      class="grid gap-2 border border-navy/15 bg-panel px-3 py-2"
      data-test="exam-converter-previous-answer-key-suggestion"
    >
      <strong class="text-xs font-semibold leading-tight text-navy/70">
        Tidigare förslag
      </strong>
      <ol
        v-if="candidateChoiceEntries.length > 0"
        class="grid gap-2"
      >
        <li
          v-for="entry in candidateChoiceEntries"
          :key="entry.id"
          class="grid grid-cols-[2rem_minmax(0,1fr)] gap-3"
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
        class="grid gap-1"
      >
        <span
          v-for="entry in candidateGapEntries"
          :key="entry.gapId"
          class="inline-flex w-fit border border-success/40 bg-success/10 px-2 py-1 text-xs font-semibold leading-tight text-success"
          :data-test="`exam-converter-advisory-gap-${entry.gapId}`"
        >
          {{ entry.label }}: {{ entry.value }}
        </span>
      </div>
    </div>

    <div class="flex flex-wrap items-center gap-2">
      <button
        type="button"
        class="btn-primary inline-flex items-center gap-2"
        :disabled="disabled || question.sourceItemFingerprint === null"
        data-test="exam-converter-accept-advisory-answer-key-action"
        @click="acceptAdvisoryAnswerKey"
      >
        Acceptera
      </button>
      <button
        type="button"
        class="btn-ghost inline-flex items-center gap-2 shadow-none"
        :disabled="disabled"
        data-test="exam-converter-edit-advisory-answer-key-action"
        @click="emit('editAdvisoryAnswerKey', question)"
      >
        <IconEdit
          :size="16"
          class="h-4 w-4"
          aria-hidden="true"
        />
        Ändra
      </button>
    </div>
  </section>
</template>
