<script setup lang="ts">
/**
 * Exam workspace enrichment notice.
 *
 * Domain purpose:
 *   The enrichment's status and lookup-failure line: the running status
 *   message while enriching, or the failed lookup message with a
 *   `Försök igen` action that runs the lookup again.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceView` where it already shows notices; the
 *     styling follows the view's notice pattern.
 *   - `useExamWorkspaceEnrichment` owns the state, this is presentation only.
 */

const props = defineProps<{
  /** The running enrichment status message; null when there is none. */
  message: string | null;
  /** The failed lookup message; null when the lookup did not fail. */
  lookupError: string | null;
}>();

const emit = defineEmits<{
  /** The teacher asked to run the failed lookup again. */
  retry: [];
}>();
</script>

<template>
  <div
    class="xw-notice xw-notice--info ws__bar"
    role="status"
    data-test="exam-workspace-enrichment"
  >
    <span
      v-if="props.lookupError"
      class="xw-grow"
      data-test="exam-workspace-enrichment-lookup-error"
    >{{ props.lookupError }}</span>
    <span
      v-else
      class="xw-grow"
      data-test="exam-workspace-enrichment-message"
    >{{ props.message }}</span>
    <button
      v-if="props.lookupError"
      type="button"
      class="xw-btn xw-btn--compact"
      data-test="exam-workspace-enrichment-lookup-retry"
      @click="emit('retry')"
    >
      Försök igen
    </button>
  </div>
</template>
