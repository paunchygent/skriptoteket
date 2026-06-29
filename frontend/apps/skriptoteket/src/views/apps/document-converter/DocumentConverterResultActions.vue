<script setup lang="ts">
/**
 * Shared file operations for the Document Converter workspace.
 *
 * Domain purpose:
 *   Keep status, retry, filename editing, download, and save actions together
 *   in the operations column regardless of whether the teacher works with an
 *   HTML/CSS project preview or a single-file conversion result.
 *
 * Relationships:
 *   - Used by `DocumentConverterView.vue`.
 *   - Receives derived route state from the project-preview, single-file, and
 *     session-history composables.
 *   - Leaves preview rendering to `DocumentConverterResultPanel.vue`.
 */

import {
  IconDownload,
  IconRefresh,
  IconVaultFiles,
} from "../../../components/icons";

defineProps<{
  actionErrorMessage: string | null;
  canDownload: boolean;
  canRetry: boolean;
  canSave: boolean;
  feedbackIsError: boolean;
  feedbackMessage: string | null;
  filenameExtension: string | null;
  filenameStem: string;
  isDownloading: boolean;
  isRetryDisabled: boolean;
  isSaving: boolean;
  resultStateLabel: string;
}>();

const emit = defineEmits<{
  download: [];
  retry: [];
  save: [];
  updateFilenameStem: [filenameStem: string];
}>();
</script>

<template>
  <section class="dc-result-actions">
    <div class="dc-result-actions__status-row">
      <div class="dc-result-actions__status-copy">
        <strong>{{ resultStateLabel }}</strong>
        <p
          v-if="feedbackMessage"
          class="dc-feedback"
          :class="{ 'dc-feedback--error': feedbackIsError }"
        >
          {{ feedbackMessage }}
        </p>
        <p
          v-if="actionErrorMessage"
          class="dc-action-error"
        >
          {{ actionErrorMessage }}
        </p>
      </div>

      <button
        v-if="canRetry"
        data-testid="document-converter-retry"
        class="dc-icon-button"
        type="button"
        aria-label="Försök igen"
        title="Försök igen"
        :disabled="isRetryDisabled"
        @click="emit('retry')"
      >
        <IconRefresh :size="16" />
      </button>
    </div>

    <label class="dc-filename-field">
      <span>Filnamn</span>
      <span class="dc-filename-field__control">
        <input
          data-testid="document-converter-filename-stem"
          type="text"
          :value="filenameStem"
          placeholder="filnamn"
          :disabled="!canDownload && !canSave"
          @input="emit('updateFilenameStem', ($event.target as HTMLInputElement).value)"
        >
        <strong v-if="filenameExtension">.{{ filenameExtension }}</strong>
      </span>
    </label>

    <div class="dc-result-actions__buttons">
      <button
        data-testid="document-converter-download"
        class="dc-neutral-button"
        type="button"
        :disabled="!canDownload || isDownloading"
        @click="emit('download')"
      >
        <IconDownload :size="16" />
        Ladda ned
      </button>
      <button
        data-testid="document-converter-save"
        class="dc-neutral-button"
        type="button"
        :disabled="!canSave || isSaving"
        @click="emit('save')"
      >
        <IconVaultFiles :size="16" />
        Spara i Mina filer
      </button>
    </div>
  </section>
</template>
