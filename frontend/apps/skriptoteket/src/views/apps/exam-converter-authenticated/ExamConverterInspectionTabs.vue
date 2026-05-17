<script setup lang="ts">
/**
 * Exam Converter inspection mode switch.
 *
 * Domain purpose:
 *   Let the teacher choose exactly one inspection mode after conversion:
 *   questions, files, or report.
 *
 * Relationships:
 *   - Rendered by `ExamConverterWorkspaceShell`.
 *   - Emits mode changes only; active mode content is rendered by siblings.
 */

import { AlertTriangle } from "lucide-vue-next";

import type { ExamConverterInspectionMode } from "./digiexamIrReviewParser";

const props = defineProps<{
  activeMode: ExamConverterInspectionMode;
  attentionCount: number;
  fileCount: number;
  questionCount: number;
}>();

const emit = defineEmits<{
  modeSelected: [mode: ExamConverterInspectionMode];
}>();

const options: { label: string; mode: ExamConverterInspectionMode }[] = [
  { label: "Frågor", mode: "questions" },
  { label: "Filer", mode: "files" },
  { label: "Rapport", mode: "report" },
];

function labelForMode(mode: ExamConverterInspectionMode): string {
  if (mode === "questions") return `Frågor (${props.questionCount})`;
  if (mode === "files") return `Filer (${props.fileCount})`;
  return "Rapport";
}

function attentionLabel(count: number): string {
  const prefix = count === 1 ? "1 fråga" : `${count.toLocaleString("sv-SE")} frågor`;
  return `${prefix} saknar facit eller poäng`;
}
</script>

<template>
  <div
    class="border-b border-navy"
    data-test="exam-converter-inspection-tabs"
  >
    <div class="flex flex-wrap items-end justify-between gap-3">
      <div
        class="grid w-full min-w-0 grid-cols-3 border border-navy border-b-0 md:max-w-[30rem]"
        role="tablist"
        aria-label="Välj granskning"
      >
        <button
          v-for="option in options"
          :key="option.mode"
          type="button"
          role="tab"
          class="min-h-10 border-r border-navy px-4 py-2 text-sm font-semibold leading-tight text-navy last:border-r-0 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action"
          :class="option.mode === activeMode ? 'bg-action/15' : 'bg-panel hover:bg-canvas'"
          :aria-selected="option.mode === activeMode"
          :data-test="`exam-converter-inspection-tab-${option.mode}`"
          @click="emit('modeSelected', option.mode)"
        >
          {{ labelForMode(option.mode) }}
        </button>
      </div>

      <p
        v-if="attentionCount > 0"
        class="mb-3 flex min-w-0 items-center gap-2 text-sm font-semibold leading-tight text-navy"
        data-test="exam-converter-inspection-attention-count"
      >
        <AlertTriangle
          class="h-5 w-5 text-warning"
          aria-hidden="true"
        />
        <span class="min-w-0 truncate">
          {{ attentionLabel(attentionCount) }}
        </span>
      </p>
    </div>
  </div>
</template>
