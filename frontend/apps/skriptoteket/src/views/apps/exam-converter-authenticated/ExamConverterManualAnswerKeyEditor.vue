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
import { Bot, Check, CheckCircle2 } from "lucide-vue-next";

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
import { isAiAnswerKeyProvenance } from "./digiexamIrQuestionReviewProjection";

const props = defineProps<{
  disabled: boolean;
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

const hasSavedAnswerKey = computed(() => props.question.effectiveAnswerKey !== null);

const selectedChoiceIdsRepresentAiAnswerKey = computed(() => {
  if (!isChoiceItem.value) return false;
  if (
    isAiAnswerKeyProvenance(props.question.currentAnswerKeyProvenance) &&
    sameNumberSet(
      selectedChoiceIds.value,
      props.question.effectiveAnswerKey?.correct_alternative_ids ?? [],
    )
  ) {
    return true;
  }
  return !hasSavedAnswerKey.value && sameNumberSet(selectedChoiceIds.value, candidateChoiceIds());
});

const canRenderEditor = computed(() => {
  const canEditQuestionType =
    (isChoiceItem.value && props.question.alternatives.length > 0) ||
    (isGapFillItem.value && props.question.gaps.length > 0);
  if (!canEditQuestionType) return false;
  return (
    props.question.missingFields.includes("Facit") ||
    hasSavedAnswerKey.value ||
    hasUsableAnswerKeyCandidate()
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
  if (props.disabled) return false;
  if (isChoiceItem.value) {
    return selectedChoiceIds.value.length > 0;
  }
  return manualGapAnswers.value.every((gapAnswer) => gapAnswer.acceptedValues.length > 0);
});

function hasUsableAnswerKeyCandidate(): boolean {
  if (!hasUsableAiSuggestion.value) return false;
  const payload = props.question.llmCandidate?.answerPayload;
  return (
    (isChoiceItem.value && payload?.kind === "choice") ||
    (isGapFillItem.value && payload?.kind === "gap_fill")
  );
}

function valuesFromDraft(value: string): string[] {
  return [...new Set(value.split(",").map((entry) => entry.trim()))].filter(
    (entry) => entry.length > 0,
  );
}

function candidateChoiceIds(): number[] {
  const payload = props.question.llmCandidate?.answerPayload;
  return payload?.kind === "choice" ? [...payload.correctAlternativeIds] : [];
}

function sameNumberSet(left: number[], right: number[]): boolean {
  if (left.length === 0 || left.length !== right.length) return false;
  const normalizedLeft = [...left].sort((a, b) => a - b);
  const normalizedRight = [...right].sort((a, b) => a - b);
  return normalizedLeft.every((value, index) => value === normalizedRight[index]);
}

function candidateGapAnswers(): Map<string, string> {
  const payload = props.question.llmCandidate?.answerPayload;
  if (payload?.kind !== "gap_fill") return new Map();
  return new Map(
    payload.gapAnswers.map((gapAnswer) => [
      gapAnswer.gapId,
      gapAnswer.acceptedValues.join(", "),
    ]),
  );
}

function resetDrafts(): void {
  selectedChoiceIds.value = props.question.effectiveAnswerKey?.correct_alternative_ids?.length
    ? [...props.question.effectiveAnswerKey.correct_alternative_ids]
    : candidateChoiceIds();
  const effectiveGapAnswers = new Map(
    (props.question.effectiveAnswerKey?.correct_gap_answers ?? []).flatMap((gapAnswer) =>
      Object.entries(gapAnswer),
    ),
  );
  const candidateAnswers = candidateGapAnswers();
  gapAnswerDrafts.value = Object.fromEntries(
    props.question.gaps.map((gap) => [
      gap.id,
      effectiveGapAnswers.get(gap.id) ?? candidateAnswers.get(gap.id) ?? "",
    ]),
  );
}

function numericAlternativeId(id: string): number | null {
  const value = Number.parseInt(id, 10);
  return Number.isInteger(value) ? value : null;
}

function toggleChoice(alternativeId: string): void {
  const numericId = numericAlternativeId(alternativeId);
  if (numericId === null) return;
  if (props.question.itemType === DIGIEXAM_ITEM_TYPE_SINGLE_CHOICE) {
    selectedChoiceIds.value = [numericId];
    return;
  }
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

watch(
  () => [
    props.question.itemId,
    props.question.effectiveAnswerKey?.correct_alternative_ids?.join(",") ?? "",
    JSON.stringify(props.question.effectiveAnswerKey?.correct_gap_answers ?? []),
    JSON.stringify(props.question.llmCandidate?.answerPayload ?? null),
  ],
  resetDrafts,
  { immediate: true },
);
</script>

<template>
  <section
    v-if="canRenderEditor"
    class="mt-4 grid gap-3 border border-navy/20 bg-canvas p-3"
    data-test="exam-converter-manual-answer-key-editor"
  >
    <h5 class="text-sm font-semibold leading-tight text-navy">
      {{ hasSavedAnswerKey ? "Ändra facit" : "Facit" }}
    </h5>
    <ol
      v-if="isChoiceItem"
      class="grid gap-2 text-sm text-navy"
    >
      <li
        v-for="alternative in question.alternatives"
        :key="alternative.id"
        class="min-w-0"
      >
        <button
          type="button"
          class="grid w-full cursor-pointer grid-cols-[2rem_minmax(0,1fr)_auto] items-start gap-3 border border-navy/15 bg-panel px-2 py-2 text-left transition-colors hover:border-action/45 hover:bg-action/5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action disabled:cursor-not-allowed disabled:opacity-50"
          :data-test="`exam-converter-manual-choice-${alternative.id}`"
          :disabled="disabled"
          :aria-pressed="selectedChoiceIds.includes(Number.parseInt(alternative.id, 10))"
          @click="toggleChoice(alternative.id)"
        >
          <span
            class="inline-grid h-7 w-7 place-items-center border text-xs font-semibold leading-none"
            :class="selectedChoiceIds.includes(Number.parseInt(alternative.id, 10)) ? 'border-success bg-success text-panel' : 'border-navy/25 bg-panel text-navy'"
          >
            {{ alternative.id }}
          </span>
          <span class="leading-relaxed">
            {{ alternative.text }}
          </span>
          <CheckCircle2
            v-if="
              selectedChoiceIds.includes(Number.parseInt(alternative.id, 10)) &&
                !selectedChoiceIdsRepresentAiAnswerKey
            "
            class="mt-1 h-5 w-5 text-success"
            data-test="exam-converter-manual-choice-teacher-symbol"
            aria-hidden="true"
          />
          <Bot
            v-if="
              selectedChoiceIds.includes(Number.parseInt(alternative.id, 10)) &&
                selectedChoiceIdsRepresentAiAnswerKey
            "
            class="mt-1 h-5 w-5 text-success"
            data-test="exam-converter-manual-choice-ai-symbol"
            aria-hidden="true"
          />
        </button>
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
          :disabled="disabled"
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
      <Check
        class="h-4 w-4"
        aria-hidden="true"
      />
      Spara facit
    </button>
  </section>
</template>
