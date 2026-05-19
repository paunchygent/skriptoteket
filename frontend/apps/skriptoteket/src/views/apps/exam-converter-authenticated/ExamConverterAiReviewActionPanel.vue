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
  title: string;
};

const copyByAction: Record<ExamConverterAiFacitReviewAction, ActionCopy> = {
  accept: {
    title: "AI-förslag till facit",
  },
  edit: {
    title: "Kontrollera facit",
  },
  review: {
    title: "Kontrollera facit",
  },
};
</script>

<template>
  <section
    class="border border-success bg-success/10 px-4 py-3"
    aria-live="polite"
    data-test="exam-converter-ai-review-action-panel"
  >
    <div class="flex items-start gap-3">
      <span
        class="grid h-10 w-10 shrink-0 place-items-center border border-success bg-panel text-success"
        aria-hidden="true"
      >
        <Bot class="h-6 w-6" />
      </span>
      <div class="min-w-0 flex-1">
        <div class="flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
          <h2 class="text-base font-semibold leading-tight text-success">
            {{ copyByAction[props.action].title }}
          </h2>
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
              Granska facit
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
              Spara alla som facit
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
              Skapa filer med facit
            </button>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
