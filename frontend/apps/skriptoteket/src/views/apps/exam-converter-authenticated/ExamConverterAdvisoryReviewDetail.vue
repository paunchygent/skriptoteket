<script setup lang="ts">
/**
 * Approved answer-key review and edit detail.
 *
 * This component owns only the teacher-facing draft and action geometry. The
 * parent persists emitted corrections and reprojects durable review state.
 */

import { computed, ref, watch } from "vue";

import {
  IconCheck,
  IconEdit,
  IconOverview,
  IconSave,
  IconX,
} from "../../../components/icons";
import type {
  ExamConverterManualAnswerKeyCorrection,
} from "./digiexamTeacherCorrectionOverlay";
import type { ExamConverterQuestionReviewRow } from "./digiexamIrReviewParser";
import ExamConverterAdvisoryAnswerKeyPanel from "./ExamConverterAdvisoryAnswerKeyPanel.vue";

const props = defineProps<{
  disabled: boolean;
  editing: boolean;
  question: ExamConverterQuestionReviewRow;
  questionCount: number;
}>();

const emit = defineEmits<{
  accept: [answerKey: ExamConverterManualAnswerKeyCorrection];
  cancel: [];
  edit: [];
  overview: [];
  save: [answerKey: ExamConverterManualAnswerKeyCorrection];
}>();

const selectedChoiceIds = ref<number[]>([]);
const gapDrafts = ref<Record<string, string>>({});

const candidatePayload = computed(() => props.question.llmCandidate?.answerPayload ?? null);

const unchangedCandidate = computed<ExamConverterManualAnswerKeyCorrection | null>(() => {
  const payload = candidatePayload.value;
  if (payload?.kind === "choice") {
    return { correctAlternativeIds: [...payload.correctAlternativeIds], kind: "choice" };
  }
  if (payload?.kind === "gap_fill") {
    return {
      gapAnswers: payload.gapAnswers.map((answer) => ({
        acceptedValues: [...answer.acceptedValues],
        gapId: answer.gapId,
      })),
      kind: "gap_fill",
    };
  }
  return null;
});

const editedAnswerKey = computed<ExamConverterManualAnswerKeyCorrection | null>(() => {
  if (candidatePayload.value?.kind === "choice") {
    return selectedChoiceIds.value.length > 0
      ? { correctAlternativeIds: [...selectedChoiceIds.value], kind: "choice" }
      : null;
  }
  if (candidatePayload.value?.kind === "gap_fill") {
    const gapAnswers = props.question.gaps.map((gap) => ({
      acceptedValues: valuesFromDraft(gapDrafts.value[gap.id] ?? ""),
      gapId: gap.id,
    }));
    return gapAnswers.every((answer) => answer.acceptedValues.length > 0)
      ? { gapAnswers, kind: "gap_fill" }
      : null;
  }
  return null;
});

function valuesFromDraft(value: string): string[] {
  return [...new Set(value.split(",").map((entry) => entry.trim()))].filter(Boolean);
}

function resetDrafts(): void {
  const payload = candidatePayload.value;
  selectedChoiceIds.value = payload?.kind === "choice" ? [...payload.correctAlternativeIds] : [];
  gapDrafts.value = Object.fromEntries(
    payload?.kind === "gap_fill"
      ? payload.gapAnswers.map((answer) => [answer.gapId, answer.acceptedValues.join(", ")])
      : [],
  );
}

function toggleChoice(alternativeId: string): void {
  const id = Number.parseInt(alternativeId, 10);
  if (!Number.isInteger(id) || props.disabled) return;
  if (props.question.itemType === "single_choice") {
    selectedChoiceIds.value = [id];
    return;
  }
  selectedChoiceIds.value = selectedChoiceIds.value.includes(id)
    ? selectedChoiceIds.value.filter((entry) => entry !== id)
    : [...selectedChoiceIds.value, id].sort((left, right) => left - right);
}

function acceptUnchanged(): void {
  if (!props.disabled && unchangedCandidate.value) emit("accept", unchangedCandidate.value);
}

function saveEdited(): void {
  if (!props.disabled && editedAnswerKey.value) emit("save", editedAnswerKey.value);
}

watch(
  () => [props.question.itemId, JSON.stringify(candidatePayload.value)],
  resetDrafts,
  { immediate: true },
);
</script>

<template>
  <article
    class="min-w-0"
    data-test="exam-converter-advisory-review-detail"
    :data-editing="editing ? 'true' : 'false'"
  >
    <header class="border-b border-navy/25 pb-5">
      <p class="text-xs font-semibold uppercase leading-tight text-navy/65">
        Fråga {{ question.sequence }} av {{ questionCount }}
      </p>
      <h3 class="mt-1 text-lg font-semibold leading-tight text-navy">
        {{ editing ? "Ändra facit" : question.title }}
      </h3>

      <div
        class="mt-4 grid grid-cols-3 gap-3"
        data-test="exam-converter-review-top-actions"
      >
        <button
          type="button"
          class="btn-ghost min-w-0 px-2 shadow-none sm:px-4"
          data-test="exam-converter-advisory-overview-action"
          @click="emit('overview')"
        >
          <IconOverview
            :size="16"
            class="h-4 w-4 shrink-0"
          />
          Översikt
        </button>
        <button
          v-if="editing"
          type="button"
          class="btn-primary min-w-0 px-2 shadow-none sm:px-4"
          :disabled="disabled || !editedAnswerKey"
          data-test="exam-converter-save-advisory-answer-key-action"
          @click="saveEdited"
        >
          <IconSave
            :size="16"
            class="h-4 w-4 shrink-0"
          />
          Spara
        </button>
        <button
          v-else
          type="button"
          class="btn-primary min-w-0 px-2 shadow-none sm:px-4"
          :disabled="disabled || !unchangedCandidate"
          data-test="exam-converter-accept-advisory-answer-key-action"
          @click="acceptUnchanged"
        >
          <IconCheck
            :size="16"
            class="h-4 w-4 shrink-0"
          />
          Godkänn
        </button>
        <button
          v-if="editing"
          type="button"
          class="btn-ghost min-w-0 px-2 shadow-none sm:px-4"
          :disabled="disabled"
          data-test="exam-converter-cancel-advisory-edit-action"
          @click="emit('cancel')"
        >
          <IconX
            :size="16"
            class="h-4 w-4 shrink-0"
          />
          Avbryt
        </button>
        <button
          v-else
          type="button"
          class="btn-ghost min-w-0 px-2 shadow-none sm:px-4"
          :disabled="disabled"
          data-test="exam-converter-edit-advisory-answer-key-action"
          @click="emit('edit')"
        >
          <IconEdit
            :size="16"
            class="h-4 w-4 shrink-0"
          />
          Ändra
        </button>
      </div>
    </header>

    <section
      v-if="editing"
      class="grid gap-4 py-5"
    >
      <ol
        v-if="candidatePayload?.kind === 'choice'"
        class="grid gap-3 md:grid-cols-2"
      >
        <li
          v-for="alternative in question.alternatives"
          :key="alternative.id"
          class="min-w-0"
        >
          <button
            type="button"
            class="grid w-full grid-cols-[2rem_minmax(0,1fr)] items-center gap-3 border bg-panel px-3 py-2 text-left text-sm text-navy"
            :class="selectedChoiceIds.includes(Number.parseInt(alternative.id, 10)) ? 'border-success bg-success/10' : 'border-navy/35'"
            :aria-pressed="selectedChoiceIds.includes(Number.parseInt(alternative.id, 10))"
            :disabled="disabled"
            :data-test="'exam-converter-advisory-edit-choice-' + alternative.id"
            @click="toggleChoice(alternative.id)"
          >
            <span class="grid h-7 w-7 place-items-center border border-navy/25 text-xs font-semibold">{{ alternative.id }}</span>
            <span class="leading-snug">{{ alternative.text }}</span>
          </button>
        </li>
      </ol>
      <div
        v-else
        class="grid gap-4 md:grid-cols-2"
      >
        <label
          v-for="gap in question.gaps"
          :key="gap.id"
          class="grid gap-1 text-sm text-navy"
        >
          <span class="text-xs font-semibold uppercase text-navy/65">{{ gap.label }}</span>
          <input
            v-model="gapDrafts[gap.id]"
            type="text"
            class="min-h-11 border border-navy bg-panel px-3 font-semibold text-navy"
            :disabled="disabled"
            :data-test="'exam-converter-advisory-edit-gap-' + gap.id"
          >
        </label>
      </div>
    </section>

    <section
      v-else
      class="grid gap-5 py-5"
    >
      <div>
        <h4 class="border-b border-navy/35 pb-2 text-base font-semibold leading-tight text-navy">Frågetext</h4>
        <p class="mt-3 text-sm leading-relaxed text-navy">{{ question.promptText }}</p>
      </div>
      <ExamConverterAdvisoryAnswerKeyPanel :question="question" />
    </section>

    <footer
      class="grid grid-cols-2 gap-3 border-t border-navy/25 pt-5"
      data-test="exam-converter-review-bottom-actions"
    >
      <button
        type="button"
        class="btn-primary min-w-0 shadow-none"
        :disabled="disabled || (editing ? !editedAnswerKey : !unchangedCandidate)"
        :data-test="editing ? 'exam-converter-save-advisory-answer-key-bottom-action' : 'exam-converter-accept-advisory-answer-key-bottom-action'"
        @click="editing ? saveEdited() : acceptUnchanged()"
      >
        <IconSave
          v-if="editing"
          :size="16"
          class="h-4 w-4 shrink-0"
        />
        <IconCheck
          v-else
          :size="16"
          class="h-4 w-4 shrink-0"
        />
        {{ editing ? "Spara" : "Godkänn" }}
      </button>
      <button
        type="button"
        class="btn-ghost min-w-0 shadow-none"
        :disabled="disabled"
        :data-test="editing ? 'exam-converter-cancel-advisory-edit-bottom-action' : 'exam-converter-edit-advisory-answer-key-bottom-action'"
        @click="editing ? emit('cancel') : emit('edit')"
      >
        <IconX
          v-if="editing"
          :size="16"
          class="h-4 w-4 shrink-0"
        />
        <IconEdit
          v-else
          :size="16"
          class="h-4 w-4 shrink-0"
        />
        {{ editing ? "Avbryt" : "Ändra" }}
      </button>
    </footer>
  </article>
</template>
