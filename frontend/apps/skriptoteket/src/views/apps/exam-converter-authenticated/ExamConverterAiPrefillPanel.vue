<script setup lang="ts">
/**
 * Exam Converter AI prefill navigation panel.
 *
 * Domain purpose:
 *   Replace the generic conversion result strip with the contextual teacher
 *   navigation shown when advisory AI answer-key candidates can seed editors.
 *
 * Relationships:
 *   - Rendered by `ExamConverterWorkspaceShell` when valid AI candidates
 *     exist.
 *   - Receives focused action state from the selected-question detail pane.
 *   - Emits navigation intent only; answer-key writes stay in the item editor.
 */

import { ListChecks } from "lucide-vue-next";

import { IconAi } from "../../../components/icons";
import type { ExamConverterAiPrefillFocus } from "./useExamConverterAiPrefillFocus";

const props = defineProps<{
  focus: ExamConverterAiPrefillFocus;
  reviewCount: number;
}>();

const emit = defineEmits<{
  openQuestions: [];
}>();

type ActionCopy = {
  title: string;
};

const copyByFocus: Record<ExamConverterAiPrefillFocus, ActionCopy> = {
  candidate: {
    title: "Kontrollera facit",
  },
  questions: {
    title: "Kontrollera facit",
  },
};
</script>

<template>
  <section
    class="border border-warning bg-warning/10 px-4 py-3"
    aria-live="polite"
    data-test="exam-converter-ai-prefill-panel"
  >
    <div class="flex items-start gap-3">
      <span
        class="grid h-10 w-10 shrink-0 place-items-center border border-warning bg-panel text-warning"
        aria-hidden="true"
      >
        <IconAi
          :size="24"
          class="h-6 w-6"
        />
      </span>
      <div class="min-w-0 flex-1">
        <div class="flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
          <h2 class="text-base font-semibold leading-tight text-navy">
            {{ copyByFocus[props.focus].title }}
          </h2>
          <div class="flex min-w-0 flex-wrap items-center justify-end gap-2">
            <span class="text-sm font-semibold leading-tight text-navy">
              {{ props.reviewCount.toLocaleString("sv-SE") }} att granska
            </span>
            <button
              type="button"
              class="btn-ghost inline-flex items-center gap-2 shadow-none"
              data-test="exam-converter-open-ai-prefill-action"
              @click="emit('openQuestions')"
            >
              <ListChecks
                class="h-4 w-4 text-action"
                aria-hidden="true"
              />
              Granska
            </button>
          </div>
        </div>
        <p class="mt-2 text-sm leading-snug text-navy/75">
          Granska frågorna som saknar rätt svar eller facitsvar.
        </p>
      </div>
    </div>
  </section>
</template>
