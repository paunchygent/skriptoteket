<script setup lang="ts">
/**
 * Exam Converter question review shell.
 *
 * Domain purpose:
 *   Render question rows and the selected-question AI-facit review pane.
 */

import { computed, ref, watch } from "vue";
import { Ban, Bot, CheckCheck, CheckCircle2, ChevronDown, Info, Pencil } from "lucide-vue-next";

import type {
  ExamConverterQuestionReviewRow,
  ExamConverterReviewProjection,
} from "./digiexamIrReviewParser";
import { hasUsableCompletionCandidate } from "./digiexamIrReviewParser";
import type {
  ExamConverterAiFacitReviewAction,
  ExamConverterReviewedSuggestionDecision,
} from "./useExamConverterAiFacitReview";
import ExamConverterQuestionNavigator from "./ExamConverterQuestionNavigator.vue";
import ExamConverterQuestionTable from "./ExamConverterQuestionTable.vue";

const props = defineProps<{
  aiFacitDecisions: Record<string, ExamConverterReviewedSuggestionDecision>;
  projection: ExamConverterReviewProjection;
}>();

const emit = defineEmits<{
  acceptEditedChoiceSuggestion: [question: ExamConverterQuestionReviewRow, correctIds: number[]];
  acceptSuggestion: [question: ExamConverterQuestionReviewRow];
  leaveSuggestion: [question: ExamConverterQuestionReviewRow];
  reviewActionFocused: [action: ExamConverterAiFacitReviewAction];
}>();

const selectedItemId = ref<string | null>(null);
const editingItemId = ref<string | null>(null);
const editedChoiceIds = ref<number[]>([]);

const selectedQuestion = computed(() => {
  return (
    props.projection.questions.find((question) => question.itemId === selectedItemId.value) ??
    props.projection.questions[0] ??
    null
  );
});

const selectedDecision = computed(() =>
  selectedQuestion.value ? props.aiFacitDecisions[selectedQuestion.value.itemId] : undefined,
);

function defaultSelectedItemId(questions: ExamConverterQuestionReviewRow[]): string | null {
  return (
    questions.find((question) => question.status === "attention")?.itemId ??
    questions[0]?.itemId ??
    null
  );
}

function selectQuestion(question: ExamConverterQuestionReviewRow): void {
  selectedItemId.value = question.itemId;
  editingItemId.value = null;
  editedChoiceIds.value = [];
  emit("reviewActionFocused", hasUsableCompletionCandidate(question) ? "accept" : "review");
}

function choiceIdsForQuestion(question: ExamConverterQuestionReviewRow): number[] {
  const payload = question.llmCandidate?.answerPayload;
  return payload?.kind === "choice" ? payload.correctAlternativeIds : [];
}

function numericAlternativeId(id: string): number | null {
  const value = Number.parseInt(id, 10);
  return Number.isInteger(value) ? value : null;
}

function isSuggestedAlternative(
  question: ExamConverterQuestionReviewRow,
  alternativeId: string,
): boolean {
  const numericId = numericAlternativeId(alternativeId);
  if (numericId === null) return false;
  if (editingItemId.value === question.itemId) {
    return editedChoiceIds.value.includes(numericId);
  }
  return choiceIdsForQuestion(question).includes(numericId);
}

function startEditing(question: ExamConverterQuestionReviewRow): void {
  if (!hasUsableCompletionCandidate(question)) return;
  const payload = question.llmCandidate?.answerPayload;
  if (payload?.kind !== "choice") return;
  editingItemId.value = question.itemId;
  editedChoiceIds.value = [...payload.correctAlternativeIds];
  emit("reviewActionFocused", "edit");
}

function toggleEditedAlternative(alternativeId: string): void {
  const numericId = numericAlternativeId(alternativeId);
  if (numericId === null) return;
  editedChoiceIds.value = editedChoiceIds.value.includes(numericId)
    ? editedChoiceIds.value.filter((id) => id !== numericId)
    : [...editedChoiceIds.value, numericId].sort((left, right) => left - right);
}

function acceptQuestion(question: ExamConverterQuestionReviewRow): void {
  if (editingItemId.value === question.itemId && editedChoiceIds.value.length > 0) {
    emit("acceptEditedChoiceSuggestion", question, editedChoiceIds.value);
  } else {
    emit("acceptSuggestion", question);
  }
  editingItemId.value = null;
  editedChoiceIds.value = [];
  emit("reviewActionFocused", "accept");
}

function leaveQuestion(question: ExamConverterQuestionReviewRow): void {
  emit("leaveSuggestion", question);
  editingItemId.value = null;
  editedChoiceIds.value = [];
  emit("reviewActionFocused", "leave");
}

function isAcceptedDecision(
  decision: ExamConverterReviewedSuggestionDecision | undefined,
): boolean {
  return decision?.outcome === "accepted_unchanged" || decision?.outcome === "teacher_edited";
}

watch(
  () => props.projection.questions,
  (questions) => {
    if (!questions.some((question) => question.itemId === selectedItemId.value)) {
      selectedItemId.value = defaultSelectedItemId(questions);
    }
  },
  { immediate: true },
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
        <div class="flex items-baseline gap-5">
          <h3 class="text-base font-semibold leading-tight text-navy">
            Fråga {{ selectedQuestion.sequence }}
          </h3>
          <span class="text-sm leading-tight text-navy/60">
            {{ selectedQuestion.itemId }}
          </span>
        </div>

        <p class="mt-5 text-sm leading-relaxed text-navy">
          {{ selectedQuestion.promptText }}
        </p>

        <section
          v-if="hasUsableCompletionCandidate(selectedQuestion)"
          class="mt-7"
          data-test="exam-converter-selected-question-ai-suggestion"
        >
          <div class="flex items-center gap-2 text-terracotta">
            <Bot
              class="h-5 w-5"
              aria-hidden="true"
            />
            <h4 class="text-base font-semibold leading-tight">
              AI-förslag
            </h4>
          </div>

          <ol class="mt-4 grid gap-2 text-sm text-navy">
            <li
              v-for="alternative in selectedQuestion.alternatives"
              :key="alternative.id"
              class="grid grid-cols-[2rem_minmax(0,1fr)_auto] items-center gap-3 border px-2 py-2"
              :class="isSuggestedAlternative(selectedQuestion, alternative.id) ? 'border-terracotta bg-terracotta/10' : 'border-navy/15 bg-panel'"
            >
              <button
                type="button"
                class="inline-grid h-7 w-7 place-items-center border text-xs font-semibold leading-none"
                :class="isSuggestedAlternative(selectedQuestion, alternative.id) ? 'border-terracotta bg-terracotta text-panel' : 'border-navy/25 bg-panel text-navy'"
                :disabled="editingItemId !== selectedQuestion.itemId"
                @click="toggleEditedAlternative(alternative.id)"
              >
                {{ alternative.id }}
              </button>
              <span class="leading-relaxed">
                {{ alternative.text }}
              </span>
              <CheckCircle2
                v-if="isSuggestedAlternative(selectedQuestion, alternative.id)"
                class="h-5 w-5 text-terracotta"
                aria-hidden="true"
              />
            </li>
          </ol>

          <div class="mt-5 flex flex-wrap items-center gap-2">
            <button
              type="button"
              class="btn-primary inline-flex items-center gap-2 shadow-none"
              :class="isAcceptedDecision(selectedDecision) ? 'bg-success' : undefined"
              data-test="exam-converter-accept-ai-suggestion-action"
              @click="acceptQuestion(selectedQuestion)"
              @focus="emit('reviewActionFocused', 'accept')"
              @mouseenter="emit('reviewActionFocused', 'accept')"
            >
              <CheckCheck
                class="h-4 w-4"
                aria-hidden="true"
              />
              {{ isAcceptedDecision(selectedDecision) ? "Godkänt" : "Godkänn" }}
            </button>
            <button
              type="button"
              class="btn-ghost inline-flex items-center gap-2 shadow-none"
              :disabled="selectedQuestion.llmCandidate?.answerPayload?.kind !== 'choice'"
              data-test="exam-converter-edit-ai-suggestion-action"
              @click="startEditing(selectedQuestion)"
              @focus="emit('reviewActionFocused', 'edit')"
              @mouseenter="emit('reviewActionFocused', 'edit')"
            >
              <Pencil
                class="h-4 w-4 text-action"
                aria-hidden="true"
              />
              Redigera
            </button>
            <button
              type="button"
              class="btn-ghost inline-flex items-center gap-2 shadow-none"
              data-test="exam-converter-leave-ai-suggestion-action"
              @click="leaveQuestion(selectedQuestion)"
              @focus="emit('reviewActionFocused', 'leave')"
              @mouseenter="emit('reviewActionFocused', 'leave')"
            >
              <Ban
                class="h-4 w-4 text-navy/70"
                aria-hidden="true"
              />
              Lämna
            </button>
          </div>

          <p class="mt-4 flex items-center gap-2 text-sm leading-snug text-navy/70">
            <Info
              class="h-4 w-4"
              aria-hidden="true"
            />
            Förslag från analysen. Läraren avgör.
          </p>
        </section>

        <section class="mt-7">
          <h4 class="border-b border-navy/35 pb-2 text-base font-semibold leading-tight text-navy">
            Finns
          </h4>
          <dl class="mt-4 grid gap-3 text-sm">
            <div class="grid grid-cols-[7rem_minmax(0,1fr)] gap-3">
              <dt class="text-navy">
                Typ
              </dt>
              <dd class="text-navy">
                {{ selectedQuestion.typeLabel }}
              </dd>
            </div>
            <div
              v-if="selectedQuestion.pointsLabel !== '—'"
              class="grid grid-cols-[7rem_minmax(0,1fr)] gap-3"
            >
              <dt class="text-navy">
                Poäng
              </dt>
              <dd class="text-navy">
                {{ selectedQuestion.pointsLabel }}
              </dd>
            </div>
          </dl>
        </section>

        <section
          v-if="selectedQuestion.alternatives.length > 0 && !hasUsableCompletionCandidate(selectedQuestion)"
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

        <section class="mt-7">
          <h4 class="border-b border-navy/35 pb-2 text-base font-semibold leading-tight text-navy">
            Saknas
          </h4>
          <div class="mt-4">
            <span
              v-if="selectedQuestion.missingFields.length === 0"
              class="text-sm text-navy/70"
            >
              —
            </span>
            <span
              v-for="missingField in selectedQuestion.missingFields"
              v-else
              :key="missingField"
              class="mr-2 inline-flex border border-warning/70 bg-panel px-2 py-1 text-sm font-medium leading-none text-warning"
            >
              {{ missingField }}
            </span>
          </div>
        </section>

        <button
          type="button"
          class="mt-7 flex w-full items-center justify-between border-t border-navy/25 pt-4 text-left text-base font-semibold leading-tight text-navy"
          data-test="exam-converter-selected-question-details-disclosure"
        >
          Detaljer
          <ChevronDown
            class="h-5 w-5"
            aria-hidden="true"
          />
        </button>
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
