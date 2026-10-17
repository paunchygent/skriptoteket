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

import { UiGlyph } from "../../../components/ui/shared";

import { UiDenseIconButton } from "../../../components/ui";

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
          :role="feedbackIsError ? 'alert' : 'status'"
          :aria-live="feedbackIsError ? 'assertive' : 'polite'"
          aria-atomic="true"
        >
          {{ feedbackMessage }}
        </p>
        <p
          v-if="actionErrorMessage"
          class="dc-action-error"
          role="alert"
          aria-live="assertive"
          aria-atomic="true"
        >
          {{ actionErrorMessage }}
        </p>
      </div>

      <UiDenseIconButton
        v-if="canRetry"
        data-testid="document-converter-retry"
        label="Försök igen"
        title="Försök igen"
        :disabled="isRetryDisabled"
        @click="emit('retry')"
      >
        <UiGlyph
          meaning="retry"
          :size="16"
          :stroke-width="2.25"
        />
      </UiDenseIconButton>
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
        class="btn-ghost"
        type="button"
        :disabled="!canDownload || isDownloading"
        @click="emit('download')"
      >
        <UiGlyph
          meaning="download"
          :size="16"
          :stroke-width="2.5"
        />
        Ladda ned
      </button>
      <button
        data-testid="document-converter-save"
        class="btn-ghost"
        type="button"
        :disabled="!canSave || isSaving"
        @click="emit('save')"
      >
        <UiGlyph
          meaning="save-to-files"
          :size="16"
          :stroke-width="2.25"
        />
        Spara i Mina filer
      </button>
    </div>
  </section>
</template>
