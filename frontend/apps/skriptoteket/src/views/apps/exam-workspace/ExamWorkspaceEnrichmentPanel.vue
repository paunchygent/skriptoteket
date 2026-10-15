<script setup lang="ts">
/**
 * Answer-key suggestion request in the exam workspace rail.
 *
 * Domain purpose:
 *   Let the teacher ask for AI answer-key suggestions for the questions as
 *   the editor shows them and show the job's current status message. When
 *   looking for a job an earlier opening lost failed, show that with a retry.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceView`; emits `request` and the view starts
 *     the job through `useExamWorkspaceEnrichment`; `retryLookup` asks the
 *     server again for the lost job.
 */

defineProps<{
  disabled: boolean;
  lookupError: string | null;
  message: string | null;
}>();

const emit = defineEmits<{
  request: [];
  retryLookup: [];
}>();
</script>

<template>
  <section
    class="grid gap-2"
    data-test="exam-workspace-enrichment"
  >
    <h2 class="text-sm font-semibold leading-tight text-navy">
      Facitförslag
    </h2>
    <p class="text-xs leading-snug text-navy/65">
      AI kan föreslå facit för frågor som saknar facit. Förslagen läggs in på frågorna och behöver granskas av dig.
    </p>
    <button
      type="button"
      class="btn-ghost justify-center shadow-none"
      :disabled="disabled"
      data-test="exam-workspace-enrichment-request"
      @click="emit('request')"
    >
      Föreslå facit
    </button>
    <p
      v-if="message"
      class="text-xs leading-snug text-navy"
      role="status"
      data-test="exam-workspace-enrichment-message"
    >
      {{ message }}
    </p>
    <template v-if="lookupError">
      <p
        class="text-xs leading-snug text-error"
        role="status"
        data-test="exam-workspace-enrichment-lookup-error"
      >
        {{ lookupError }}
      </p>
      <button
        type="button"
        class="btn-ghost justify-self-start shadow-none"
        data-test="exam-workspace-enrichment-lookup-retry"
        @click="emit('retryLookup')"
      >
        Försök igen
      </button>
    </template>
  </section>
</template>
