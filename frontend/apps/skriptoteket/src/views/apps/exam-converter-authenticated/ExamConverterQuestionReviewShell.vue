<script setup lang="ts">
/**
 * Exam Converter question review shell.
 *
 * The shell switches between one overview and one focused question. Durable
 * correction truth remains owned by the parent projection and persistence path.
 */

import { computed, ref, toRef, watch } from "vue";

import { IconOverview } from "../../../components/icons";
import type {
  ExamConverterQuestionReviewRow,
  ExamConverterReviewProjection,
} from "./digiexamIrReviewParser";
import { hasUsableCompletionCandidate } from "./digiexamIrReviewParser";
import type { ExamConverterAiPrefillFocus } from "./useExamConverterAiPrefillFocus";
import type {
  ExamConverterItemTextPatchCorrection,
  ExamConverterManualAnswerKeyCorrection,
} from "./digiexamTeacherCorrectionOverlay";
import ExamConverterAdvisoryReviewDetail from "./ExamConverterAdvisoryReviewDetail.vue";
import ExamConverterEffectiveAnswerKeySummary from "./ExamConverterEffectiveAnswerKeySummary.vue";
import ExamConverterItemTextPatchEditor from "./ExamConverterItemTextPatchEditor.vue";
import ExamConverterManualAnswerKeyEditor from "./ExamConverterManualAnswerKeyEditor.vue";
import ExamConverterPointCorrectionEditor from "./ExamConverterPointCorrectionEditor.vue";
import ExamConverterQuestionNavigator from "./ExamConverterQuestionNavigator.vue";
import ExamConverterQuestionTable from "./ExamConverterQuestionTable.vue";
import { useExamConverterAdvisoryAnswerKeyMode } from "./useExamConverterAdvisoryAnswerKeyMode";

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
  aiPrefillFocused: [focus: ExamConverterAiPrefillFocus];
}>();

const selectedItemId = ref<string | null>(null);
const detailOpen = ref(false);
const advisoryEditItemId = ref<string | null>(null);
const pendingAdvanceFromItemId = ref<string | null>(null);
const {
  canShowAnswerKeyEditor,
  isPendingAdvisoryQuestion,
} = useExamConverterAdvisoryAnswerKeyMode(toRef(props, "projection"));

const selectedQuestion = computed(() =>
  props.projection.questions.find((question) => question.itemId === selectedItemId.value) ??
  props.projection.questions[0] ??
  null,
);

const selectedQuestionIsPendingAdvisory = computed(
  () => selectedQuestion.value ? isPendingAdvisoryQuestion(selectedQuestion.value) : false,
);

const showsAnswerKeyEditor = computed(
  () => selectedQuestion.value ? canShowAnswerKeyEditor(selectedQuestion.value) : false,
);

function isUnresolvedQuestion(question: ExamConverterQuestionReviewRow): boolean {
  return question.answerKeyReviewState === "review_required" || question.status === "attention";
}

function firstUnresolvedQuestion(
  questions: ExamConverterQuestionReviewRow[],
): ExamConverterQuestionReviewRow | null {
  return questions.find(isUnresolvedQuestion) ?? null;
}

function defaultSelectedItemId(questions: ExamConverterQuestionReviewRow[]): string | null {
  return firstUnresolvedQuestion(questions)?.itemId ?? questions[0]?.itemId ?? null;
}

function nextUnresolvedQuestion(
  currentQuestion: ExamConverterQuestionReviewRow,
  questions: ExamConverterQuestionReviewRow[],
): ExamConverterQuestionReviewRow | null {
  const startIndex = questions.findIndex((question) => question.itemId === currentQuestion.itemId);
  if (startIndex === -1) return firstUnresolvedQuestion(questions);
  const ordered = [...questions.slice(startIndex + 1), ...questions.slice(0, startIndex)];
  return ordered.find(isUnresolvedQuestion) ?? null;
}

function selectQuestion(question: ExamConverterQuestionReviewRow): void {
  selectedItemId.value = question.itemId;
  advisoryEditItemId.value = null;
  detailOpen.value = true;
  emit("aiPrefillFocused", hasUsableCompletionCandidate(question) ? "candidate" : "questions");
}

function showOverview(): void {
  detailOpen.value = false;
  advisoryEditItemId.value = null;
  emit("aiPrefillFocused", "questions");
}

function acceptAdvisory(answerKey: ExamConverterManualAnswerKeyCorrection): void {
  const question = selectedQuestion.value;
  if (!question) return;
  pendingAdvanceFromItemId.value = question.itemId;
  emit("applyManualAnswerKey", question, answerKey);
}

function applyManualAnswerKey(
  question: ExamConverterQuestionReviewRow,
  answerKey: ExamConverterManualAnswerKeyCorrection,
): void {
  pendingAdvanceFromItemId.value = question.itemId;
  emit("applyManualAnswerKey", question, answerKey);
}

function advanceAfterSavedReview(): void {
  const pendingItemId = pendingAdvanceFromItemId.value;
  if (!pendingItemId || props.isCorrectionApplying) return;
  const savedQuestion = props.projection.questions.find(
    (question) => question.itemId === pendingItemId,
  );
  if (!savedQuestion) {
    pendingAdvanceFromItemId.value = null;
    showOverview();
    return;
  }
  if (isUnresolvedQuestion(savedQuestion)) return;
  pendingAdvanceFromItemId.value = null;
  advisoryEditItemId.value = null;
  const nextQuestion = nextUnresolvedQuestion(savedQuestion, props.projection.questions);
  if (nextQuestion) {
    selectQuestion(nextQuestion);
    return;
  }
  showOverview();
}

watch(
  () => props.projection.questions,
  (questions) => {
    const selected = questions.find((question) => question.itemId === selectedItemId.value);
    if (!selected) selectedItemId.value = defaultSelectedItemId(questions);
    if (selected && !isPendingAdvisoryQuestion(selected)) advisoryEditItemId.value = null;
  },
  { immediate: true },
);

watch(
  () => props.aiSuggestionFocusKey,
  () => {
    const unresolved = firstUnresolvedQuestion(props.projection.questions);
    if (unresolved) {
      selectQuestion(unresolved);
      return;
    }
    selectedItemId.value = defaultSelectedItemId(props.projection.questions);
    showOverview();
  },
);

watch(
  () => [props.projection.questions, props.isCorrectionApplying] as const,
  advanceAfterSavedReview,
);
</script>

<template>
  <section
    class="min-h-0 min-w-0 flex-1 py-5"
    :class="{ 'is-detail-open': detailOpen }"
    data-test="exam-converter-question-review-shell"
  >
    <div
      v-if="!detailOpen"
      class="min-w-0"
      data-test="exam-converter-question-list-surface"
    >
      <h3 class="text-base font-semibold leading-tight text-navy">
        Att hantera
      </h3>

      <div
        v-if="projection.questions.length === 0"
        class="mt-6 border border-dashed border-navy/35 bg-canvas px-5 py-8 text-sm text-navy/70"
      >
        Inga frågor att visa.
      </div>

      <ExamConverterQuestionTable
        v-else
        class="exam-converter-question-table mt-4 hidden md:table"
        :questions="projection.questions"
        :selected-item-id="selectedQuestion?.itemId ?? null"
        @question-selected="selectQuestion"
      />

      <ExamConverterQuestionNavigator
        v-if="projection.questions.length > 0"
        class="exam-converter-question-navigator mt-4 md:hidden"
        :questions="projection.questions"
        :selected-item-id="selectedQuestion?.itemId ?? null"
        @question-selected="selectQuestion"
      />
    </div>

    <div
      v-else-if="selectedQuestion"
      class="min-w-0"
      data-test="exam-converter-selected-question-detail"
      :data-selected-item-id="selectedQuestion.itemId"
    >
      <ExamConverterAdvisoryReviewDetail
        v-if="selectedQuestionIsPendingAdvisory"
        :disabled="isCorrectionApplying"
        :editing="advisoryEditItemId === selectedQuestion.itemId"
        :question="selectedQuestion"
        :question-count="projection.questions.length"
        @accept="acceptAdvisory"
        @cancel="advisoryEditItemId = null"
        @edit="advisoryEditItemId = selectedQuestion.itemId"
        @overview="showOverview"
        @save="acceptAdvisory"
      />

      <template v-else>
        <header class="border-b border-navy/25 pb-4">
          <p class="text-xs font-semibold uppercase leading-tight text-navy/65">
            Fråga {{ selectedQuestion.sequence }} av {{ projection.questions.length }}
          </p>
          <h3 class="mt-1 text-lg font-semibold leading-tight text-navy">
            {{ selectedQuestion.title }}
          </h3>
          <button
            type="button"
            class="btn-ghost mt-4 inline-flex shadow-none"
            data-test="exam-converter-detail-overview-action"
            @click="showOverview"
          >
            <IconOverview
              :size="16"
              class="h-4 w-4"
            />
            Översikt
          </button>
        </header>

        <ExamConverterItemTextPatchEditor
          :disabled="isCorrectionApplying"
          :question="selectedQuestion"
          @apply-item-text-patch="(question, patch) => emit('applyItemTextPatch', question, patch)"
        />

        <section
          v-if="selectedQuestion.reviewWarnings.length > 0"
          class="mt-5 grid gap-2 border border-navy/25 bg-canvas px-4 py-3"
          data-test="exam-converter-selected-question-source-repair-messages"
        >
          <p
            v-for="warning in selectedQuestion.reviewWarnings"
            :key="warning.code"
            class="text-sm leading-snug text-navy"
          >
            {{ warning.message }}
          </p>
        </section>

        <section class="mt-5 grid gap-4">
          <ExamConverterEffectiveAnswerKeySummary :question="selectedQuestion" />
          <ExamConverterPointCorrectionEditor
            :disabled="isCorrectionApplying"
            :question="selectedQuestion"
            @apply-point-correction="(question, maxScore) => emit('applyPointCorrection', question, maxScore)"
          />
          <ExamConverterManualAnswerKeyEditor
            v-if="showsAnswerKeyEditor"
            :disabled="isCorrectionApplying"
            :question="selectedQuestion"
            @apply-manual-answer-key="applyManualAnswerKey"
          />
        </section>

        <section
          v-if="selectedQuestion.alternatives.length > 0 && !showsAnswerKeyEditor"
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
              <span class="inline-grid h-7 w-7 place-items-center border border-navy/25 text-xs font-semibold leading-none">
                {{ alternative.id }}
              </span>
              <span class="leading-relaxed">{{ alternative.text }}</span>
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
              <dt class="text-navy">Luckor</dt>
              <dd class="text-navy">{{ selectedQuestion.lucktextStructure.gapCount }}</dd>
            </div>
            <div class="grid grid-cols-[7rem_minmax(0,1fr)] gap-3">
              <dt class="text-navy">Bilder</dt>
              <dd class="text-navy">{{ selectedQuestion.lucktextStructure.imageCount }}</dd>
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
                <span v-if="image.dimensionsLabel"> · {{ image.dimensionsLabel }}</span>
              </figcaption>
            </figure>
          </div>
        </section>
      </template>
    </div>
  </section>
</template>
