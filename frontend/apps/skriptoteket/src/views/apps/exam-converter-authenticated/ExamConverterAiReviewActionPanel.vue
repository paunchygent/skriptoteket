<script setup lang="ts">
/**
 * Exam Converter AI-facit action panel.
 *
 * Domain purpose:
 *   Replace the generic conversion result strip with the contextual teacher
 *   action guidance shown while reviewing advisory AI-facit candidates.
 *
 * Relationships:
 *   - Rendered by `ExamConverterWorkspaceShell` when valid AI-facit candidates
 *     exist.
 *   - Receives focused action state from the selected-question detail pane.
 *   - Emits navigation and bulk-accept intent only.
 */

import { Bot, CheckCheck, FilePlus2, ListChecks } from "lucide-vue-next";

import type { ExamConverterAiFacitReviewAction } from "./useExamConverterAiFacitReview";

const props = defineProps<{
  acceptedCount: number;
  action: ExamConverterAiFacitReviewAction;
  canApplyReviewedSuggestions: boolean;
  suggestionCount: number;
}>();

const emit = defineEmits<{
  acceptAllSuggestions: [];
  applyReviewedSuggestions: [];
  openQuestions: [];
}>();

type ActionCopy = {
  body: string;
  title: string;
};

const copyByAction: Record<ExamConverterAiFacitReviewAction, ActionCopy> = {
  accept: {
    body: "Sparar förslaget som granskat facit för den valda frågan.",
    title: "Godkänn AI-facit",
  },
  edit: {
    body: "Öppnar förslaget så att facit kan justeras innan det godkänns.",
    title: "Redigera AI-facit",
  },
  leave: {
    body: "Lämnar frågan utan granskat AI-facit.",
    title: "Lämna frågan",
  },
  review: {
    body: "Kontrollera föreslagna facit innan du skapar eller sparar filer.",
    title: "Granska AI-facit",
  },
};
</script>

<template>
  <section
    class="border border-terracotta bg-terracotta/10 px-4 py-3"
    aria-live="polite"
    data-test="exam-converter-ai-review-action-panel"
  >
    <div class="grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-4">
      <span
        class="grid h-10 w-10 place-items-center border border-terracotta bg-panel text-terracotta"
        aria-hidden="true"
      >
        <Bot class="h-6 w-6" />
      </span>
      <div class="min-w-0">
        <h2 class="text-base font-semibold leading-tight text-terracotta">
          {{ copyByAction[props.action].title }}
        </h2>
        <p class="mt-1 text-sm leading-snug text-navy">
          {{ copyByAction[props.action].body }}
        </p>
        <p class="mt-1 text-sm leading-snug text-navy/70">
          Filer skapas först när granskningen skickas in.
        </p>
      </div>
      <div class="flex shrink-0 items-center gap-2">
        <button
          type="button"
          class="btn-ghost inline-flex items-center gap-2 shadow-none"
          data-test="exam-converter-open-ai-review-action"
          @click="emit('openQuestions')"
        >
          <ListChecks
            class="h-4 w-4 text-action"
            aria-hidden="true"
          />
          Granska
        </button>
        <button
          type="button"
          class="btn-ghost inline-flex items-center gap-2 shadow-none"
          :disabled="props.acceptedCount >= props.suggestionCount"
          data-test="exam-converter-accept-all-ai-suggestions-action"
          @click="emit('acceptAllSuggestions')"
        >
          <CheckCheck
            class="h-4 w-4"
            aria-hidden="true"
          />
          Godkänn alla
        </button>
        <button
          type="button"
          class="btn-primary inline-flex items-center gap-2 shadow-none"
          :disabled="!props.canApplyReviewedSuggestions"
          data-test="exam-converter-apply-reviewed-ai-suggestions-action"
          @click="emit('applyReviewedSuggestions')"
        >
          <FilePlus2
            class="h-4 w-4"
            aria-hidden="true"
          />
          Skapa filer
        </button>
      </div>
    </div>
  </section>
</template>
