<script setup lang="ts">
/**
 * Exam Converter result strip.
 *
 * Domain purpose:
 *   Present one global conversion outcome at the top of the authenticated Exam
 *   Converter workspace without duplicating status across question, file, or
 *   report modes.
 *
 * Relationships:
 *   - Rendered by `ExamConverterWorkspaceShell`.
 *   - Receives teacher-facing state from `useExamConverterConversionState`.
 *   - Emits intent only; question navigation is introduced by a later slice.
 */

import { AlertCircle, CheckCircle2, XCircle } from "lucide-vue-next";

import ExamConverterConversionProgress from "./ExamConverterConversionProgress.vue";
import type { ExamConverterResultStripState } from "./useExamConverterConversionState";

defineProps<{
  result: ExamConverterResultStripState;
}>();

const emit = defineEmits<{
  openQuestions: [];
}>();

const containerClassByTone: Record<ExamConverterResultStripState["tone"], string> = {
  error: "border-error bg-error/10",
  info: "border-navy/25 bg-panel-muted",
  success: "border-success bg-success/10",
  warning: "border-warning bg-warning/10",
};

const iconClassByTone: Record<ExamConverterResultStripState["tone"], string> = {
  error: "text-error",
  info: "text-action",
  success: "text-success",
  warning: "text-warning",
};
</script>

<template>
  <section
    class="border px-4 py-3"
    :class="containerClassByTone[result.tone]"
    aria-live="polite"
    data-test="exam-converter-result-strip"
  >
    <div
      class="grid items-start gap-4"
      :class="result.status === 'running' ? 'grid-cols-[minmax(0,1fr)_auto]' : 'grid-cols-[auto_minmax(0,1fr)_auto]'"
    >
      <span
        v-if="result.status !== 'running'"
        class="mt-0.5 grid h-8 w-8 place-items-center border border-current bg-panel"
        :class="iconClassByTone[result.tone]"
        aria-hidden="true"
      >
        <CheckCircle2
          v-if="result.status === 'success'"
          class="h-5 w-5"
        />
        <AlertCircle
          v-else-if="result.status === 'partial'"
          class="h-5 w-5"
        />
        <XCircle
          v-else
          class="h-5 w-5"
        />
      </span>
      <div class="min-w-0">
        <h2 class="text-sm font-semibold leading-tight text-navy md:text-base">
          {{ result.title }}
        </h2>
        <p
          v-if="result.detail"
          class="mt-1 text-sm leading-snug text-navy"
        >
          {{ result.detail }}
        </p>
        <p
          v-if="result.nextAction"
          class="mt-2 text-sm leading-snug text-navy/70"
        >
          {{ result.nextAction }}
        </p>
        <ExamConverterConversionProgress
          v-if="result.progress"
          :progress="result.progress"
        />
      </div>
      <button
        v-if="result.actionLabel"
        type="button"
        class="btn-ghost shrink-0 justify-center shadow-none"
        data-test="exam-converter-result-open-questions"
        @click="emit('openQuestions')"
      >
        {{ result.actionLabel }}
      </button>
    </div>
  </section>
</template>
