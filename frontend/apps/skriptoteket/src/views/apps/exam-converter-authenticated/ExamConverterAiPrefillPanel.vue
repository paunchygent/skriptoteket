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

import {
  IconAi,
  IconCheck,
  IconClipboardList,
} from "../../../components/icons";
import type { ExamConverterAiPrefillFocus } from "./useExamConverterAiPrefillFocus";

const props = defineProps<{
  disabled: boolean;
  focus: ExamConverterAiPrefillFocus;
  reviewCount: number;
}>();

const emit = defineEmits<{
  acceptAllAdvisoryCandidates: [];
  openQuestions: [];
}>();

</script>

<template>
  <section
    class="border border-warning bg-warning/10 px-4 py-3 sm:px-6 sm:py-5"
    aria-live="polite"
    data-test="exam-converter-ai-prefill-panel"
  >
    <div class="grid gap-3 md:grid-cols-[2.5rem_minmax(0,1fr)_minmax(0,24rem)] md:items-center md:gap-5">
      <div class="flex min-w-0 items-center gap-3 md:contents">
        <span
          class="grid h-10 w-10 shrink-0 place-items-center border border-warning bg-panel text-warning"
          aria-hidden="true"
        >
          <IconAi
            :size="24"
            class="h-6 w-6"
          />
        </span>
        <div class="min-w-0">
          <h2 class="text-base font-semibold leading-tight text-navy">
            Föreslagna facit
          </h2>
          <p class="mt-1 text-sm leading-snug text-navy/75">
            {{ props.reviewCount.toLocaleString("sv-SE") }} att granska.
          </p>
        </div>
      </div>
      <div
        class="grid grid-cols-2 gap-2 md:gap-3"
        data-test="exam-converter-ai-prefill-actions"
      >
        <button
          type="button"
          class="btn-ghost min-w-0 w-full px-2 text-[0.6875rem] leading-tight tracking-[0.055em] shadow-none sm:px-3 sm:text-xs"
          :disabled="disabled"
          data-test="exam-converter-open-ai-prefill-action"
          @click="emit('openQuestions')"
        >
          <IconClipboardList
            :size="16"
            class="h-4 w-4 shrink-0"
          />
          Granska
        </button>
        <button
          type="button"
          class="btn-ghost min-w-0 w-full px-2 text-[0.6875rem] leading-tight tracking-[0.055em] shadow-none sm:px-3 sm:text-xs"
          :disabled="disabled"
          data-test="exam-converter-accept-all-ai-prefill-action"
          @click="emit('acceptAllAdvisoryCandidates')"
        >
          <IconCheck
            :size="16"
            class="h-4 w-4 shrink-0"
          />
          Godkänn alla
        </button>
      </div>
    </div>
  </section>
</template>
