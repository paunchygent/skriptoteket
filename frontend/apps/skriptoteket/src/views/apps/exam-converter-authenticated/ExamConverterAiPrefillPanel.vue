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
        <div>
          <h2 class="text-base font-semibold leading-tight text-navy">
            {{ copyByFocus[props.focus].title }}
          </h2>
          <p class="mt-1 text-sm leading-snug text-navy/75">
            {{ props.reviewCount.toLocaleString("sv-SE") }} frågor att granska.
          </p>
        </div>
        <div
          class="mt-3 grid grid-cols-2 gap-3"
          data-test="exam-converter-ai-prefill-actions"
        >
          <button
            type="button"
            class="btn-primary min-w-0 shadow-none"
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
            class="btn-ghost min-w-0 shadow-none"
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
    </div>
  </section>
</template>
