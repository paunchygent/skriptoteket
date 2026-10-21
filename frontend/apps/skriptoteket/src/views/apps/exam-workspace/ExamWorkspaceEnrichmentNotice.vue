<script setup lang="ts">
/**
 * Exam workspace enrichment notice.
 *
 * Domain purpose:
 *   The one notice row under the workspace header for AI answer-key
 *   suggestions: the current enrichment message, or the failed lost-job
 *   lookup with its `Försök igen` retry. It renders nothing while neither
 *   a message nor a lookup error is set.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceView` where it already shows notices; the
 *     styling follows the view's notice pattern.
 *   - The enrichment session (`useExamWorkspaceEnrichment`) owns the message,
 *     the lookup error and the retry; this is presentation only.
 */

import type { useExamWorkspaceEnrichment } from "./useExamWorkspaceEnrichment";

const props = defineProps<{
  /** The enrichment session whose message, lookup error and retry this shows. */
  enrichment: ReturnType<typeof useExamWorkspaceEnrichment>;
}>();
</script>

<template>
  <div
    v-if="props.enrichment.enrichmentMessage.value || props.enrichment.enrichmentLookupError.value"
    class="xw-notice xw-notice--info ws__bar"
    role="status"
    data-test="exam-workspace-enrichment"
  >
    <span
      v-if="props.enrichment.enrichmentLookupError.value"
      class="xw-grow"
      data-test="exam-workspace-enrichment-lookup-error"
    >{{ props.enrichment.enrichmentLookupError.value }}</span>
    <span
      v-else
      class="xw-grow"
      data-test="exam-workspace-enrichment-message"
    >{{ props.enrichment.enrichmentMessage.value }}</span>
    <button
      v-if="props.enrichment.enrichmentLookupError.value"
      type="button"
      class="xw-btn xw-btn--compact"
      data-test="exam-workspace-enrichment-lookup-retry"
      @click="props.enrichment.retryEnrichmentLookup"
    >
      Försök igen
    </button>
  </div>
</template>
