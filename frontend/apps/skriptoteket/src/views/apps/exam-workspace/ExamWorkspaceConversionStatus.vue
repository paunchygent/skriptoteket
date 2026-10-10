<script setup lang="ts">
/** Conversion progress and status recovery notice for the workspace host. */
defineProps<{
  conversionMessage: string | null;
  conversionError: string | null;
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
