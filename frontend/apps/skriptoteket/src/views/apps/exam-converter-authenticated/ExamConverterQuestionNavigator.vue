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

import { Bot, CheckCircle2, XCircle } from "lucide-vue-next";

import type { ExamConverterQuestionReviewRow } from "./digiexamIrReviewParser";
import { visibleMissingFieldsForQuestion } from "./digiexamIrReviewParser";

defineProps<{
  questions: ExamConverterQuestionReviewRow[];
  selectedItemId: string | null;
}>();

const emit = defineEmits<{
  questionSelected: [question: ExamConverterQuestionReviewRow];
}>();

</script>

<template>
  <div class="grid gap-2">
    <button
      v-for="question in questions"
      :key="question.itemId"
      type="button"
      :aria-selected="question.itemId === selectedItemId ? 'true' : 'false'"
      class="grid min-w-0 grid-cols-[2rem_minmax(0,1fr)_auto] gap-2 border px-2.5 py-2.5 text-left text-navy hover:bg-canvas focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action"
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
        <span class="mt-2 flex flex-wrap items-center gap-1">
          <span class="border border-navy/20 bg-panel px-1.5 py-0.5 text-[0.6875rem] font-medium leading-none text-navy/75">
            {{ question.typeLabel }}
          </span>
          <span
            v-for="missingField in visibleMissingFieldsForQuestion(question)"
            :key="missingField"
            class="border border-warning/70 bg-panel px-1.5 py-0.5 text-[0.6875rem] font-medium leading-none text-warning"
          >
            {{ missingField }}
          </span>
        </span>
      </span>
      <span
        class="inline-grid h-6 w-6 place-items-center"
        :aria-label="question.statusSymbol === 'ai_suggestion' ? 'AI-förslag' : question.statusSymbol === 'complete' ? 'Klar' : 'Saknar facit'"
        role="img"
      >
        <Bot
          v-if="question.statusSymbol === 'ai_suggestion'"
          class="h-4 w-4 text-success"
          aria-hidden="true"
        />
        <CheckCircle2
          v-else-if="question.statusSymbol === 'complete'"
          class="h-4 w-4 text-success"
          aria-hidden="true"
        />
        <XCircle
          v-else
          class="h-4 w-4 text-error"
          aria-hidden="true"
        />
      </span>
    </button>
  </div>
</template>
