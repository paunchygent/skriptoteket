<script setup lang="ts">
/**
 * Conversion Hub mode tabs.
 *
 * Domain purpose:
 *   Let signed-in teachers switch between bespoke Conversion Hub lanes without
 *   exposing generic tool-run mechanics.
 *
 * Relationships:
 *   - Rendered by `ExamConverterAuthenticatedView`.
 *   - Selects between Exam Converter and transcript intake hosts.
 */

import type { ConversionHubMode } from "./conversionHubModeRoute";

defineProps<{
  activeMode: ConversionHubMode;
}>();

const emit = defineEmits<{
  modeSelected: [mode: ConversionHubMode];
}>();
</script>

<template>
  <nav
    class="mx-auto mb-3 flex w-full max-w-[90rem] flex-wrap gap-2"
    aria-label="Conversion Hub"
  >
    <button
      type="button"
      class="border px-3 py-2 text-sm font-semibold leading-tight focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action"
      :class="activeMode === 'exam' ? 'border-navy bg-navy text-button-primary-text' : 'border-navy/25 bg-panel text-navy'"
      data-test="conversion-hub-mode-exam"
      :aria-pressed="activeMode === 'exam'"
      @click="emit('modeSelected', 'exam')"
    >
      Prov
    </button>
    <button
      type="button"
      class="border px-3 py-2 text-sm font-semibold leading-tight focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action"
      :class="activeMode === 'transcript' ? 'border-navy bg-navy text-button-primary-text' : 'border-navy/25 bg-panel text-navy'"
      data-test="conversion-hub-mode-transcript"
      :aria-pressed="activeMode === 'transcript'"
      @click="emit('modeSelected', 'transcript')"
    >
      Transkript
    </button>
  </nav>
</template>
