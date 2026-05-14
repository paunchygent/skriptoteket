<script setup lang="ts">
/**
 * Exam Converter conversion progress visualization.
 *
 * Domain purpose:
 *   Show teacher-visible movement while an Exam Converter job is running,
 *   without claiming exact upstream ETA before Sir Convert exposes progress
 *   events.
 *
 * Relationships:
 *   - Rendered only by `ExamConverterResultStrip` for running conversion.
 *   - Receives local scaffold progress from `useExamConverterConversionState`.
 *   - Becomes the binding point for a future upstream progress stream.
 */

import type { ExamConverterRunningProgress } from "./useExamConverterConversionState";

defineProps<{
  progress: ExamConverterRunningProgress;
}>();

</script>

<template>
  <div
    class="mt-3 grid gap-2"
    data-test="exam-converter-conversion-progress"
  >
    <div class="flex items-baseline justify-between gap-3 text-xs leading-none text-navy/70">
      <span
        class="font-medium text-navy"
        data-test="exam-converter-progress-stage"
      >
        {{ progress.stageLabel }}
      </span>
      <span
        class="font-mono tabular-nums"
        data-test="exam-converter-progress-percent"
      >
        {{ progress.percent }} %
      </span>
    </div>
    <div
      class="h-2 border border-navy/25 bg-panel"
      role="progressbar"
      aria-label="Konverteringens framdrift"
      :aria-valuenow="progress.percent"
      aria-valuemin="0"
      aria-valuemax="100"
    >
      <div
        class="h-full bg-action transition-[width] duration-700 ease-out"
        :style="{ width: `${progress.percent}%` }"
        data-test="exam-converter-progress-bar"
      />
    </div>
    <p
      v-if="progress.isLongRunning"
      class="text-xs leading-snug text-navy/70"
      data-test="exam-converter-long-running-copy"
    >
      Det här tar längre tid än vanligt. Sidan uppdateras när nästa steg är klart.
    </p>
  </div>
</template>
