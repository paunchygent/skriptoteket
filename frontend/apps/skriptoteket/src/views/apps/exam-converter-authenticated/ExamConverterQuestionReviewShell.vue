<script setup lang="ts">
/**
 * Exam Converter question review shell.
 *
 * Domain purpose:
 *   Render question rows and the selected-question correction editor.
 */

import { computed, ref, watch } from "vue";
import type {
  ExamConverterQuestionReviewRow,
  ExamConverterReviewProjection,
} from "./digiexamIrReviewParser";
import {
  hasUsableCompletionCandidate,
} from "./digiexamIrReviewParser";
import type { ExamConverterAiFacitReviewAction } from "./useExamConverterAiFacitReview";
import type { ExamConverterManualAnswerKeyCorrection } from "./digiexamTeacherCorrectionOverlay";
import type { ExamConverterItemTextPatchCorrection } from "./digiexamTeacherCorrectionOverlay";
import ExamConverterEffectiveAnswerKeySummary from "./ExamConverterEffectiveAnswerKeySummary.vue";
import ExamConverterItemTextPatchEditor from "./ExamConverterItemTextPatchEditor.vue";
import ExamConverterManualAnswerKeyEditor from "./ExamConverterManualAnswerKeyEditor.vue";
import ExamConverterPointCorrectionEditor from "./ExamConverterPointCorrectionEditor.vue";
import ExamConverterQuestionNavigator from "./ExamConverterQuestionNavigator.vue";
import ExamConverterQuestionTable from "./ExamConverterQuestionTable.vue";

const props = defineProps<{
  aiSuggestionFocusKey: number;
  isCorrectionApplying: boolean;
  projection: ExamConverterReviewProjection;
}>();

const emit = defineEmits<{
  applyManualAnswerKey: [
    question: ExamConverterQuestionReviewRow,
    answerKey: ExamConverterManualAnswerKeyCorrection,
  ];
  applyItemTextPatch: [
    question: ExamConverterQuestionReviewRow,
    patch: ExamConverterItemTextPatchCorrection,
  ];
  applyPointCorrection: [question: ExamConverterQuestionReviewRow, maxScore: number];
  reviewActionFocused: [action: ExamConverterAiFacitReviewAction];
}>();

const selectedItemId = ref<string | null>(null);

const selectedQuestion = computed(() => {
  return (
    props.projection.questions.find((question) => question.itemId === selectedItemId.value) ??
    props.projection.questions[0] ??
    null
  );
});

const showsAnswerKeyEditor = computed(() => {
  const question = selectedQuestion.value;
  if (!question) return false;
  const editableQuestionType = question.alternatives.length > 0 || question.gaps.length > 0;
  return editableQuestionType && (
    question.missingFields.includes("Facit") ||
    question.effectiveAnswerKey !== null ||
    hasUsableCompletionCandidate(question)
  );
});

function firstAiSuggestedQuestion(questions: ExamConverterQuestionReviewRow[]): ExamConverterQuestionReviewRow | null {
  return questions.find(hasUsableCompletionCandidate) ?? null;
}

function defaultSelectedItemId(questions: ExamConverterQuestionReviewRow[]): string | null {
  return (
    firstAiSuggestedQuestion(questions)?.itemId ??
    questions.find((question) => question.status === "attention")?.itemId ??
    questions[0]?.itemId ??
    null
  );
}

function nextAiSuggestedQuestionId(
  currentQuestion: ExamConverterQuestionReviewRow,
  questions: ExamConverterQuestionReviewRow[],
): string | null {
  const startIndex = questions.findIndex((question) => question.itemId === currentQuestion.itemId);
  if (startIndex === -1) return firstAiSuggestedQuestion(questions)?.itemId ?? null;
  const orderedQuestions = [
    ...questions.slice(startIndex + 1),
    ...questions.slice(0, startIndex),
  ];
  return orderedQuestions.find(hasUsableCompletionCandidate)?.itemId ?? null;
}

function selectQuestion(question: ExamConverterQuestionReviewRow): void {
  selectedItemId.value = question.itemId;
  emit("reviewActionFocused", hasUsableCompletionCandidate(question) ? "edit" : "review");
}

function applyManualAnswerKey(
  question: ExamConverterQuestionReviewRow,
  answerKey: ExamConverterManualAnswerKeyCorrection,
): void {
  emit("applyManualAnswerKey", question, answerKey);
  const nextItemId = nextAiSuggestedQuestionId(question, props.projection.questions);
  if (nextItemId) {
    selectedItemId.value = nextItemId;
  }
}

watch(
  () => props.projection.questions,
  (questions) => {
    const selectedQuestionAfterUpdate = questions.find(
      (question) => question.itemId === selectedItemId.value,
    );
    if (!selectedQuestionAfterUpdate) {
      selectedItemId.value = defaultSelectedItemId(questions);
    }
  },
  { immediate: true },
);

watch(
  () => props.aiSuggestionFocusKey,
  () => {
    const firstSuggestedQuestion = firstAiSuggestedQuestion(props.projection.questions);
    selectedItemId.value =
      firstSuggestedQuestion?.itemId ?? defaultSelectedItemId(props.projection.questions);
  },
);
</script>

<template>
  <section
    class="exam-converter-question-review-shell grid min-h-0 min-w-0 flex-1 gap-5 py-5"
    data-test="exam-converter-question-review-shell"
  >
    <div class="min-w-0 overflow-hidden">
      <h3 class="text-base font-semibold leading-tight text-navy">
        Frågor att kontrollera
      </h3>

      <div
        v-if="projection.questions.length === 0"
        class="mt-6 border border-dashed border-navy/35 bg-canvas px-5 py-8 text-sm text-navy/70"
      >
        Inga frågor att visa.
      </div>

      <ExamConverterQuestionTable
        v-else
        class="exam-converter-question-table mt-6"
        :questions="projection.questions"
        :selected-item-id="selectedQuestion?.itemId ?? null"
        @question-selected="selectQuestion"
      />

      <ExamConverterQuestionNavigator
        v-if="projection.questions.length > 0"
        class="exam-converter-question-navigator mt-4"
        :questions="projection.questions"
        :selected-item-id="selectedQuestion?.itemId ?? null"
        @question-selected="selectQuestion"
      />
    </div>

    <aside
      class="exam-converter-question-detail min-w-0 border-l border-navy/35 pl-5"
      data-test="exam-converter-selected-question-detail"
    >
      <template v-if="selectedQuestion">
        <ExamConverterItemTextPatchEditor
          :disabled="isCorrectionApplying"
          :question="selectedQuestion"
          @apply-item-text-patch="(question, patch) => emit('applyItemTextPatch', question, patch)"
        />

        <section class="mt-5 grid gap-4">
          <ExamConverterEffectiveAnswerKeySummary :question="selectedQuestion" />
          <ExamConverterPointCorrectionEditor
            :disabled="isCorrectionApplying"
            :question="selectedQuestion"
            @apply-point-correction="(question, maxScore) => emit('applyPointCorrection', question, maxScore)"
          />
          <ExamConverterManualAnswerKeyEditor
            :disabled="isCorrectionApplying"
            :question="selectedQuestion"
            @apply-manual-answer-key="applyManualAnswerKey"
          />
        </section>

        <section
          v-if="selectedQuestion.alternatives.length > 0 && !hasUsableCompletionCandidate(selectedQuestion) && !showsAnswerKeyEditor"
          class="mt-7"
          data-test="exam-converter-selected-question-alternatives"
        >
          <h4 class="border-b border-navy/35 pb-2 text-base font-semibold leading-tight text-navy">
            Alternativ
          </h4>
          <ol class="mt-4 grid gap-2 text-sm text-navy">
            <li
              v-for="alternative in selectedQuestion.alternatives"
              :key="alternative.id"
              class="grid grid-cols-[2rem_minmax(0,1fr)] gap-3"
            >
              <span
                class="inline-grid h-7 w-7 place-items-center border border-navy/25 text-xs font-semibold leading-none"
              >
                {{ alternative.id }}
              </span>
              <span class="leading-relaxed">
                {{ alternative.text }}
              </span>
            </li>
          </ol>
        </section>

        <section
          v-if="selectedQuestion.lucktextStructure"
          class="mt-7"
          data-test="exam-converter-selected-question-lucktext"
        >
          <h4 class="border-b border-navy/35 pb-2 text-base font-semibold leading-tight text-navy">
            Lucktext
          </h4>
          <dl class="mt-4 grid gap-3 text-sm">
            <div class="grid grid-cols-[7rem_minmax(0,1fr)] gap-3">
              <dt class="text-navy">
                Luckor
              </dt>
              <dd class="text-navy">
                {{ selectedQuestion.lucktextStructure.gapCount }}
              </dd>
            </div>
            <div class="grid grid-cols-[7rem_minmax(0,1fr)] gap-3">
              <dt class="text-navy">
                Bilder
              </dt>
              <dd class="text-navy">
                {{ selectedQuestion.lucktextStructure.imageCount }}
              </dd>
            </div>
          </dl>
          <div
            v-if="selectedQuestion.lucktextStructure.images.length > 0"
            class="mt-4 grid gap-3"
          >
            <figure
              v-for="image in selectedQuestion.lucktextStructure.images"
              :key="image.id"
              class="border border-navy/20 p-3"
            >
              <img
                v-if="image.dataUrl"
                :alt="image.altText"
                class="max-h-56 max-w-full object-contain"
                :src="image.dataUrl"
              >
              <figcaption class="mt-2 text-xs leading-tight text-navy/70">
                {{ image.altText }}
                <span v-if="image.dimensionsLabel">
                  · {{ image.dimensionsLabel }}
                </span>
              </figcaption>
            </figure>
          </div>
        </section>
      </template>
    </aside>
  </section>
</template>

<style scoped>
.exam-converter-question-review-shell {
  grid-template-columns: minmax(0, 1.45fr) minmax(16rem, 0.72fr);
}

.exam-converter-question-navigator {
  display: none;
}

@media (max-width: 1199px) {
  .exam-converter-question-review-shell {
    grid-template-columns: minmax(12rem, 0.42fr) minmax(0, 1fr);
    gap: 1rem;
    overflow-x: visible;
  }

  .exam-converter-question-table {
    display: none;
  }

  .exam-converter-question-navigator {
    display: grid;
  }

  .exam-converter-question-detail {
    padding-left: 1rem;
  }
}
</style>
