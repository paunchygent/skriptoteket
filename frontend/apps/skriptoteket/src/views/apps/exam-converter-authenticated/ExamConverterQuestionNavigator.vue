<script setup lang="ts">
/**
 * Exam Converter question navigator.
 *
 * Domain purpose:
 *   Provide the reduced-width review navigator used when the question table
 *   would compete with the selected-question inspector for workspace space.
 *
 * Relationships:
 *   - Rendered by `ExamConverterQuestionReviewShell`.
 *   - Uses the review projection rows produced by `digiexamIrReviewParser`.
 */

import {
  IconAi,
  IconCheck,
  IconEdit,
  IconNextPage,
  IconWarning,
} from "../../../components/icons";

import type { ExamConverterQuestionReviewRow } from "./digiexamIrReviewParser";

defineProps<{
  questions: ExamConverterQuestionReviewRow[];
  selectedItemId: string | null;
}>();

const emit = defineEmits<{
  questionSelected: [question: ExamConverterQuestionReviewRow];
}>();

function statusSymbolLabel(question: ExamConverterQuestionReviewRow): string {
  if (question.statusSymbol === "ai_suggestion") return "Förslag";
  if (question.statusSymbol === "validation_required") return "Saknar facit";
  return question.answerKeyReviewStateLabel;
}
</script>

<template>
  <div class="grid gap-2">
    <button
      v-for="question in questions"
      :key="question.itemId"
      type="button"
      :aria-selected="question.itemId === selectedItemId ? 'true' : 'false'"
      class="grid min-w-0 grid-cols-[2rem_minmax(0,1fr)_5.75rem_1rem] items-center gap-2 border px-2.5 py-2.5 text-left text-navy hover:bg-canvas focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action"
      :class="question.itemId === selectedItemId ? 'border-navy bg-navy/5 shadow-[inset_4px_0_0_var(--color-navy)]' : 'border-navy/15 bg-panel'"
      :data-test="`exam-converter-question-navigator-row-${question.itemId}`"
      role="option"
      @click="emit('questionSelected', question)"
    >
      <span class="pt-0.5 text-sm font-semibold leading-tight">
        {{ question.sequence }}.
      </span>
      <span class="min-w-0">
        <span class="line-clamp-2 text-sm font-medium leading-snug">
          {{ question.promptText }}
        </span>
      </span>
      <span
        class="inline-flex min-w-0 items-center gap-1.5 text-left"
        :aria-label="statusSymbolLabel(question)"
        role="img"
      >
        <IconAi
          v-if="question.statusSymbol === 'ai_suggestion'"
          :size="18"
          class="h-4 w-4 shrink-0 text-navy"
          aria-hidden="true"
        />
        <IconCheck
          v-else-if="question.statusSymbol === 'complete'"
          :size="18"
          class="h-4 w-4 text-success"
          aria-hidden="true"
        />
        <IconEdit
          v-else-if="question.statusSymbol === 'teacher_modified'"
          :size="18"
          class="h-4 w-4 text-navy"
          aria-hidden="true"
        />
        <IconWarning
          v-else
          :size="18"
          class="h-4 w-4 shrink-0 text-warning"
          aria-hidden="true"
        />
        <span class="text-[0.6875rem] font-semibold leading-tight">
          {{ statusSymbolLabel(question) }}
        </span>
      </span>
      <IconNextPage
        :size="18"
        class="h-[1.125rem] w-[1.125rem] shrink-0 text-navy/65"
        aria-hidden="true"
      />
    </button>
  </div>
</template>
