<script setup lang="ts">
/**
 * Exam Converter advisory retry panel.
 *
 * Domain purpose:
 *   Present the approved teacher retry action when facit suggestions could not
 *   be produced for the authenticated Exam Converter review flow.
 *
 * Relationships:
 *   - Rendered by `ExamConverterWorkspaceShell` beside the normal review
 *     status area.
 *   - Emits only the explicit retry intent; transport and idempotency stay in
 *     the authenticated runtime bridge.
 */

import { RefreshCw } from "lucide-vue-next";

defineProps<{
  disabled: boolean;
}>();

const emit = defineEmits<{
  retry: [];
}>();
</script>

<template>
  <div
    class="mt-3 flex flex-wrap items-center justify-between gap-3 border border-navy/25 bg-canvas px-3 py-3"
    data-test="exam-converter-advisory-retry-panel"
  >
    <p class="text-sm font-medium leading-snug text-navy">
      Det gick inte att ta fram ett facitförslag.
    </p>
    <button
      type="button"
      class="btn-secondary inline-flex min-h-10 items-center gap-2 px-3 py-2 text-sm"
      :disabled="disabled"
      data-test="exam-converter-advisory-retry-action"
      @click="emit('retry')"
    >
      <RefreshCw
        class="h-4 w-4"
        aria-hidden="true"
      />
      <span>Försök igen</span>
    </button>
  </div>
</template>
