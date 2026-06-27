<script setup lang="ts">
/**
 * Result preview panel for the Document Converter route.
 *
 * Domain purpose:
 *   Show the active session result, keep preview/download/save actions close
 *   to it, and present a clear empty or failed state when no preview is ready.
 *
 * Relationships:
 *   - Used by `DocumentConverterView.vue`.
 *   - Receives derived state from `useDocumentConverterSessionHistory`.
 *   - Emits teacher actions back to the route host.
 */

import {
  IconDownload,
  IconFileText,
  IconVaultFiles,
} from "../../../components/icons";

type ArtifactOption = {
  artifactId: string;
  filename: string;
};

defineProps<{
  actionErrorMessage: string | null;
  activePreviewUrl: string | null;
  artifactOptions: ArtifactOption[];
  activeArtifactId: string | null;
  canDownload: boolean;
  canSave: boolean;
  isDownloading: boolean;
  isSaving: boolean;
  resultTitle: string;
  resultStateLabel: string;
  sourceLabel: string | null;
  resultTypeLabel: string | null;
}>();

const emit = defineEmits<{
  download: [];
  save: [];
  selectArtifact: [artifactId: string];
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
      <aside
        v-if="artifactOptions.length > 1"
        class="dc-artifact-list"
        aria-label="PDF"
      >
        <button
          v-for="artifact in artifactOptions"
          :key="artifact.artifactId"
          class="dc-artifact-list__item"
          :class="{ 'dc-artifact-list__item--active': artifact.artifactId === activeArtifactId }"
          type="button"
          @click="emit('selectArtifact', artifact.artifactId)"
        >
          <IconFileText :size="16" />
          {{ artifact.filename }}
        </button>
      </aside>

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
          <span v-if="actionErrorMessage">
            {{ actionErrorMessage }}
          </span>
        </div>
      </section>
    </div>

    <footer class="dc-preview-footer">
      <p
        v-if="actionErrorMessage"
        class="dc-action-error"
      >
        {{ actionErrorMessage }}
      </p>
      <span
        v-else-if="sourceLabel && resultTypeLabel"
        class="dc-result-format"
      >
        {{ sourceLabel }} • {{ resultTypeLabel }}
      </span>
      <div class="dc-footer-actions">
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
    </footer>
  </section>
</template>
