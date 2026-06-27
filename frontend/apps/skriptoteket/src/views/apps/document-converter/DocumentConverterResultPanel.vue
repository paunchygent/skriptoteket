<script setup lang="ts">
/**
 * Result preview panel for the Document Converter route.
 *
 * Domain purpose:
 *   Show the active session result preview while leaving file operations and
 *   output selection to the shared middle-column controls.
 *
 * Relationships:
 *   - Used by `DocumentConverterView.vue`.
 *   - Receives derived state from `useDocumentConverterSessionHistory`.
 *   - Leaves teacher actions to the operations-column controls.
 */
defineProps<{
  activePreviewUrl: string | null;
  resultTitle: string;
  resultStateLabel: string;
}>();
</script>

<template>
  <section
    class="dc-preview"
    aria-label="Resultat"
  >
    <header class="dc-preview-header">
      <h2>{{ resultTitle }}</h2>
    </header>

    <div class="dc-preview-body">
      <section
        class="dc-artifact-result"
        aria-label="Resultat"
      >
        <iframe
          v-if="activePreviewUrl"
          data-testid="document-converter-pdf-frame"
          class="dc-artifact-frame"
          :src="activePreviewUrl"
          :title="resultTitle"
        />
        <div
          v-else
          class="dc-result-empty"
        >
          <strong>{{ resultStateLabel }}</strong>
        </div>
      </section>
    </div>
  </section>
</template>
