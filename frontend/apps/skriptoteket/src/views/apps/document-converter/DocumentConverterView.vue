<script setup lang="ts">
/**
 * Route-visible Document Converter workspace.
 *
 * Domain purpose:
 *   Let authenticated teachers build a small HTML/CSS project preview and
 *   save or download the resulting PDF through Skriptoteket-owned endpoints.
 *
 * Relationships:
 *   - Mounted by the authenticated `/apps/document-converter` route.
 *   - Uses route-local preview state and API modules.
 *   - Uses canonical icon wrappers from `src/components/icons`.
 */

import { ref } from "vue";

import {
  IconCode,
  IconCombinePdf,
  IconDownload,
  IconFileText,
  IconImageAsset,
  IconRefresh,
  IconSeparatePdfs,
  IconVaultFiles,
} from "../../../components/icons";
import {
  UiSegmentedTileToggle,
  UiSegmentedToggle,
  type UiSegmentedTileToggleOption,
  type UiSegmentedToggleOption,
} from "../../../components/ui";
import type {
  DocumentConverterProjectOutputMode,
  DocumentConverterProjectPaperSize,
} from "./documentConverterProjectPreviewApi";
import "./documentConverterWorkspace.css";
import "./documentConverterPreview.css";
import { useDocumentConverterProjectPreview } from "./useDocumentConverterProjectPreview";

type DocumentConverterOutputChoice = UiSegmentedTileToggleOption & {
  value: DocumentConverterProjectOutputMode;
};

type DocumentConverterPaperChoice = UiSegmentedToggleOption & {
  value: DocumentConverterProjectPaperSize;
};

const outputChoices: DocumentConverterOutputChoice[] = [
  {
    label: "Enskilda PDF-filer",
    value: "separate_pdfs",
    ariaLabel: "Skapa en PDF per dokument",
    icon: IconSeparatePdfs,
    dataTest: "document-converter-output-separate_pdfs",
  },
  {
    label: "Kombinerad PDF",
    value: "combined_pdf",
    ariaLabel: "Skapa en kombinerad PDF",
    icon: IconCombinePdf,
    dataTest: "document-converter-output-combined_pdf",
  },
];

const paperChoices: DocumentConverterPaperChoice[] = [
  { label: "A3", value: "a3", dataTest: "document-converter-paper-a3" },
  { label: "A4", value: "a4", dataTest: "document-converter-paper-a4" },
  { label: "A5", value: "a5", dataTest: "document-converter-paper-a5" },
];

const {
  canRetryPreview,
  downloadSelectedArtifact,
  errorMessage,
  fileSummary,
  isCurrentPreviewReady,
  isDownloading,
  isPreviewRunning,
  isSaving,
  onFilesDropped,
  onFilesSelected,
  outputMode,
  paperSize,
  preview,
  previewPdfUrl,
  retryPreview,
  saveSelectedArtifact,
  selectArtifact,
  selectOutputMode,
  selectPaperSize,
  selectedArtifact,
  selectedFileLabel,
  selectedHtmlFile,
  selectedHtmlFilename,
  statusMessage,
  totalProjectFiles,
} = useDocumentConverterProjectPreview();

const fileInputElement = ref<HTMLInputElement | null>(null);

function openFilePicker(): void {
  fileInputElement.value?.click();
}
</script>

<template>
  <main
    class="dc-workbench"
    aria-label="Dokumentkonverterare"
  >
    <header class="dc-topbar">
      <h1>DOKUMENTKONVERTERARE</h1>
    </header>

    <section
      class="dc-mobile-summary"
      aria-label="Mobilöversikt"
    >
      <div
        class="dc-mobile-project"
        aria-label="Projektöversikt"
      >
        <h1>{{ selectedFileLabel() }}</h1>
        <span>{{ totalProjectFiles }} filer</span>
        <span>{{ fileSummary.html.length }} HTML</span>
        <span>{{ fileSummary.css.length }} CSS</span>
        <span>{{ fileSummary.images.length }} bilder</span>
      </div>
    </section>

    <section class="dc-workspace">
      <aside
        class="dc-rail"
        aria-label="Projekt"
      >
        <section class="dc-assets">
          <div class="dc-asset-heading">
            <h2>HTML ({{ fileSummary.html.length }}/10)</h2>
          </div>
          <button
            v-for="file in fileSummary.html"
            :key="file.name"
            class="dc-asset-row"
            :class="{ 'dc-asset-row--active': file.name === selectedHtmlFile?.name }"
            type="button"
            @click="selectedHtmlFilename = file.name"
          >
            <IconFileText :size="16" />
            {{ file.name }}
          </button>

          <div class="dc-asset-heading dc-asset-heading--spaced">
            <h2>CSS ({{ fileSummary.css.length }}/10)</h2>
          </div>
          <div
            v-for="file in fileSummary.css"
            :key="file.name"
            class="dc-asset-row dc-asset-row--static"
          >
            <IconCode :size="16" />
            {{ file.name }}
          </div>

          <div class="dc-asset-heading dc-asset-heading--spaced">
            <h2>Bilder ({{ fileSummary.images.length }}/20)</h2>
          </div>
          <div
            v-for="file in fileSummary.images"
            :key="file.name"
            class="dc-asset-row dc-asset-row--static"
          >
            <IconImageAsset :size="16" />
            {{ file.name }}
          </div>
        </section>
      </aside>

      <section
        class="dc-controls"
        aria-label="Val för export"
      >
        <div class="dc-file-toolbar">
          <div
            data-testid="document-converter-dropzone"
            class="dc-dropzone"
            role="button"
            tabindex="0"
            @click="openFilePicker"
            @keydown.enter.prevent="openFilePicker"
            @keydown.space.prevent="openFilePicker"
            @dragover.prevent
            @drop="onFilesDropped"
          >
            <strong>Dra filer hit eller klicka</strong>
            <span>HTML, CSS och bilder</span>
          </div>
          <input
            ref="fileInputElement"
            data-testid="document-converter-file-input"
            class="dc-file-input"
            type="file"
            multiple
            accept=".html,.htm,.css,.png,.jpg,.jpeg,.webp"
            @change="onFilesSelected"
          >
        </div>

        <section class="dc-control-section">
          <div class="dc-field">
            <span>Exportera som</span>
            <UiSegmentedTileToggle
              :model-value="outputMode"
              :options="outputChoices"
              aria-label="Exportera som"
              @update:model-value="(value) => selectOutputMode(value as DocumentConverterProjectOutputMode)"
            />
          </div>

          <div class="dc-field">
            <span>Format</span>
            <UiSegmentedToggle
              :model-value="paperSize"
              :options="paperChoices"
              aria-label="Format"
              variant="subrail"
              width="full"
              :columns="3"
              @update:model-value="(value) => selectPaperSize(value as DocumentConverterProjectPaperSize)"
            />
          </div>
        </section>

        <div
          v-if="statusMessage || errorMessage"
          class="dc-feedback-row"
        >
          <p
            class="dc-feedback"
            :class="{ 'dc-feedback--error': errorMessage }"
          >
            {{ statusMessage ?? errorMessage }}
          </p>
          <button
            v-if="canRetryPreview"
            data-testid="document-converter-retry"
            class="dc-icon-button"
            type="button"
            aria-label="Försök igen"
            title="Försök igen"
            :disabled="isPreviewRunning"
            @click="retryPreview"
          >
            <IconRefresh :size="16" />
          </button>
        </div>
      </section>

      <section
        class="dc-preview"
        aria-label="Förhandsvisning"
      >
        <header class="dc-preview-header">
          <h2>{{ selectedArtifact?.filename ?? selectedFileLabel() }}</h2>
        </header>

        <div class="dc-preview-body">
          <aside
            v-if="(preview?.artifacts.length ?? 0) > 1"
            class="dc-artifact-list"
            aria-label="PDF"
          >
            <button
              v-for="artifact in preview?.artifacts ?? []"
              :key="artifact.artifact_id"
              class="dc-artifact-list__item"
              :class="{ 'dc-artifact-list__item--active': artifact.artifact_id === selectedArtifact?.artifact_id }"
              type="button"
              @click="selectArtifact(artifact.artifact_id)"
            >
              <IconFileText :size="16" />
              {{ artifact.filename }}
            </button>
          </aside>

          <section
            class="dc-artifact-result"
            aria-label="PDF"
          >
            <iframe
              v-if="previewPdfUrl"
              data-testid="document-converter-pdf-frame"
              class="dc-artifact-frame"
              :src="previewPdfUrl"
              :title="selectedArtifact?.filename ?? selectedFileLabel()"
            />
          </section>
        </div>

        <footer class="dc-preview-footer">
          <div class="dc-preview-meta">
            <h2>{{ selectedArtifact?.filename ?? selectedFileLabel() }}</h2>
          </div>
          <div class="dc-footer-actions">
            <button
              data-testid="document-converter-download"
              class="dc-neutral-button"
              type="button"
              :disabled="!isCurrentPreviewReady || isDownloading"
              @click="downloadSelectedArtifact"
            >
              <IconDownload :size="16" />
              Ladda ned
            </button>
            <button
              data-testid="document-converter-save"
              class="dc-neutral-button"
              type="button"
              :disabled="!isCurrentPreviewReady || isSaving"
              @click="saveSelectedArtifact"
            >
              <IconVaultFiles :size="16" />
              Spara i Mina filer
            </button>
          </div>
        </footer>
      </section>
    </section>
  </main>
</template>
