<script setup lang="ts">
/**
 * Exam Converter manual answer-key editor.
 *
 * Domain purpose:
 *   Collect teacher-authored answer keys for source-bound choice and gap-fill
 *   corrections without mutating the source IR or file-readiness state.
 *
 * Relationships:
 *   - Rendered inside `ExamConverterQuestionReviewShell`.
 *   - Emits a bounded correction draft consumed by
 *     `digiexamTeacherCorrectionOverlay`.
 *   - Stays separate from advisory AI-facit candidate review state.
 */

import { computed, ref, watch } from "vue";
import { CheckCheck } from "lucide-vue-next";

import {
  DIGIEXAM_ITEM_TYPE_GAP_FILL,
  DIGIEXAM_ITEM_TYPE_MULTIPLE_CHOICE,
  DIGIEXAM_ITEM_TYPE_MULTIPLE_RESPONSE,
  DIGIEXAM_ITEM_TYPE_SINGLE_CHOICE,
} from "../../../api/sirConvertGateway/contractValues";
import type {
  ExamConverterManualAnswerKeyCorrection,
} from "./digiexamTeacherCorrectionOverlay";
import type { ExamConverterQuestionReviewRow } from "./digiexamIrReviewParser";

const props = defineProps<{
  question: ExamConverterQuestionReviewRow;
}>();

const emit = defineEmits<{
  applyManualAnswerKey: [
    question: ExamConverterQuestionReviewRow,
    answerKey: ExamConverterManualAnswerKeyCorrection,
  ];
}>();

const selectedChoiceIds = ref<number[]>([]);
const gapAnswerDrafts = ref<Record<string, string>>({});

const isChoiceItem = computed(() =>
  props.question.itemType === DIGIEXAM_ITEM_TYPE_MULTIPLE_CHOICE ||
  props.question.itemType === DIGIEXAM_ITEM_TYPE_MULTIPLE_RESPONSE ||
  props.question.itemType === DIGIEXAM_ITEM_TYPE_SINGLE_CHOICE,
);

const isGapFillItem = computed(() => props.question.itemType === DIGIEXAM_ITEM_TYPE_GAP_FILL);

const hasUsableAiSuggestion = computed(
  () =>
    props.question.llmCandidate?.decisionState === "suggested" &&
    props.question.llmCandidate.validationState === "valid" &&
    props.question.llmCandidate.answerPayload !== null,
);

const canRenderEditor = computed(() => {
  if (!props.question.missingFields.includes("Facit") || hasUsableAiSuggestion.value) {
    return false;
  }
  return (
    (isChoiceItem.value && props.question.alternatives.length > 0) ||
    (isGapFillItem.value && props.question.gaps.length > 0)
  );
});

const manualGapAnswers = computed(() =>
  props.question.gaps.map((gap) => ({
    acceptedValues: valuesFromDraft(gapAnswerDrafts.value[gap.id] ?? ""),
    gapId: gap.id,
  })),
);

const canApplyManualAnswerKey = computed(() => {
  if (!canRenderEditor.value || props.question.sourceItemFingerprint === null) {
    return false;
  }
  if (isChoiceItem.value) {
    return selectedChoiceIds.value.length > 0;
  }
  return manualGapAnswers.value.every((gapAnswer) => gapAnswer.acceptedValues.length > 0);
});

function valuesFromDraft(value: string): string[] {
  return [...new Set(value.split(",").map((entry) => entry.trim()))].filter(
    (entry) => entry.length > 0,
  );
}

function resetDrafts(): void {
  selectedChoiceIds.value = [];
  gapAnswerDrafts.value = Object.fromEntries(
    props.question.gaps.map((gap) => [gap.id, ""]),
  );
}

function numericAlternativeId(id: string): number | null {
  const value = Number.parseInt(id, 10);
  return Number.isInteger(value) ? value : null;
}

function toggleChoice(alternativeId: string): void {
  const numericId = numericAlternativeId(alternativeId);
  if (numericId === null) return;
  selectedChoiceIds.value = selectedChoiceIds.value.includes(numericId)
    ? selectedChoiceIds.value.filter((id) => id !== numericId)
    : [...selectedChoiceIds.value, numericId].sort((left, right) => left - right);
}

function applyManualAnswerKey(): void {
  if (!canApplyManualAnswerKey.value) return;
  emit(
    "applyManualAnswerKey",
    props.question,
    isChoiceItem.value
      ? {
          correctAlternativeIds: selectedChoiceIds.value,
          kind: "choice",
        }
      : {
          gapAnswers: manualGapAnswers.value,
          kind: "gap_fill",
        },
  );
}

watch(() => props.question.itemId, resetDrafts, { immediate: true });
</script>

<template>
  <section
    v-if="canRenderEditor"
    class="mt-4 grid gap-3 border border-navy/20 bg-canvas p-3"
    data-test="exam-converter-manual-answer-key-editor"
  >
    <h5 class="text-sm font-semibold leading-tight text-navy">
      Facit
    </h5>
    <ol
      v-if="isChoiceItem"
      class="grid gap-2 text-sm text-navy"
    >
      <li
        v-for="alternative in question.alternatives"
        :key="alternative.id"
        class="grid grid-cols-[2rem_minmax(0,1fr)] items-start gap-3 border border-navy/15 bg-panel px-2 py-2"
      >
        <button
          type="button"
          class="inline-grid h-7 w-7 place-items-center border text-xs font-semibold leading-none"
          :class="selectedChoiceIds.includes(Number.parseInt(alternative.id, 10)) ? 'border-success bg-success text-panel' : 'border-navy/25 bg-panel text-navy'"
          :data-test="`exam-converter-manual-choice-${alternative.id}`"
          @click="toggleChoice(alternative.id)"
        >
          {{ alternative.id }}
        </button>
        <span class="leading-relaxed">
          {{ alternative.text }}
        </span>
      </li>
    </ol>
    <div
      v-else
      class="grid gap-2"
    >
      <label
        v-for="gap in question.gaps"
        :key="gap.id"
        class="grid gap-1 text-sm text-navy"
      >
        <span class="font-semibold">
          {{ gap.label }}
        </span>
        <input
          v-model="gapAnswerDrafts[gap.id]"
          class="min-h-10 border border-navy/35 bg-panel px-3 text-sm text-navy"
          :data-test="`exam-converter-manual-gap-${gap.id}`"
          type="text"
        >
      </label>
    </div>
    <button
      type="button"
      class="btn-ghost inline-flex w-fit items-center gap-2 shadow-none"
      :disabled="!canApplyManualAnswerKey"
      data-test="exam-converter-apply-manual-answer-key-action"
      @click="applyManualAnswerKey"
    >
      <CheckCheck
        class="h-4 w-4"
        aria-hidden="true"
      />
      Skicka facit
    </button>
  </section>
</template>
