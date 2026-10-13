<script setup lang="ts">
/** Conversion progress, status recovery notice and overall batch progress for the workspace host. */
defineProps<{
  conversionMessage: string | null;
  conversionError: string | null;
  conversionProgress: { done: number; total: number } | null;
  isConverting: boolean;
}>();

defineEmits<{
  retry: [];
}>();
</script>

<template>
  <div
    v-if="conversionMessage"
    class="grid gap-2 border-b border-navy bg-canvas px-4 py-2 text-sm leading-snug"
    role="status"
    aria-live="polite"
    data-test="exam-workspace-conversion-status"
  >
    <p>{{ conversionMessage }}</p>
    <div
      v-if="conversionProgress"
      class="h-2 border border-navy bg-canvas"
      role="progressbar"
      aria-label="Konverterade frågor"
      :aria-valuemax="conversionProgress.total"
      :aria-valuenow="conversionProgress.done"
      aria-valuemin="0"
      data-test="exam-workspace-conversion-progress"
    >
      <div
        class="h-full bg-navy"
        :style="{ width: `${(100 * conversionProgress.done) / conversionProgress.total}%` }"
      />
    </div>
    <p
      v-if="conversionProgress && conversionProgress.done > 0"
      class="text-xs"
    >
      Klara frågor går att redigera direkt. Frågor som konverteras visar källtexten tills de är klara.
    </p>
    <template v-if="isConverting && conversionError">
      <p class="text-error">{{ conversionError }}</p>
      <button
        type="button"
        class="btn-ghost justify-self-start shadow-none"
        data-test="exam-workspace-conversion-retry"
        @click="$emit('retry')"
      >
        Försök igen
      </button>
    </template>
    <p v-else-if="!isConverting">
      Välj provfilen igen i Filer för att försöka på nytt.
    </p>
  </div>
</template>
