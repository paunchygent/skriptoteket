<script setup lang="ts">
/**
 * Answer-key proposal request in the exam workspace rail.
 *
 * Domain purpose:
 *   Let the teacher ask for advisory answer-key proposals for the saved
 *   version and show the job's current status message.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceView`; emits `request` and the view starts
 *     the job through `useExamWorkspaceEnrichment`.
 */

defineProps<{
  disabled: boolean;
  message: string | null;
}>();

const emit = defineEmits<{
  request: [];
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
      AI kan föreslå facit för frågor som saknar facit. Du granskar varje förslag innan det används.
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
  </section>
</template>
