<script setup lang="ts">
/**
 * Route-visible Document Converter workspace.
 *
 * Domain purpose:
 *   Let authenticated teachers switch between HTML/CSS project previews and
 *   owner-scoped file conversions while keeping the current usable result
 *   easy to download, save, or retry.
 *
 * Relationships:
 *   - Mounted by the authenticated `/apps/document-converter` route.
 *   - Uses route-local project-preview, single-file, and session-history
 *     composables.
 */
import { computed, ref } from "vue";

import {
  IconCombinePdf,
  IconSeparatePdfs,
} from "../../../components/icons";
import {
  UiSegmentedToggle,
  type UiSegmentedTileToggleOption,
  type UiSegmentedToggleOption,
  UiSegmentedTileToggle,
} from "../../../components/ui";
import DocumentConverterArtifactSelector from "./DocumentConverterArtifactSelector.vue";
import DocumentConverterResultActions from "./DocumentConverterResultActions.vue";
import DocumentConverterResultPanel from "./DocumentConverterResultPanel.vue";
import DocumentConverterSourceIntake from "./DocumentConverterSourceIntake.vue";
import DocumentConverterSourcePanel from "./DocumentConverterSourcePanel.vue";
import DocumentConverterSingleFileControls from "./DocumentConverterSingleFileControls.vue";
import {
  type DocumentConverterProjectOutputMode,
  type DocumentConverterProjectPaperSize,
} from "./documentConverterProjectPreviewApi";
import "./documentConverterWorkspace.css";
import "./documentConverterPreview.css";
import { useDocumentConverterFilenameIntent } from "./useDocumentConverterFilenameIntent";
import { useDocumentConverterProjectPreview } from "./useDocumentConverterProjectPreview";
import { useDocumentConverterHistoryBridge } from "./useDocumentConverterHistoryBridge";
import { useDocumentConverterSessionHistory } from "./useDocumentConverterSessionHistory";
import {
  useDocumentConverterSingleFile,
  type DocumentConverterSingleFileOutput,
  type DocumentConverterSingleFileSource,
} from "./useDocumentConverterSingleFile";

type DocumentConverterWorkspaceMode = "project_preview" | "single_file";
type DocumentConverterOutputChoice = UiSegmentedTileToggleOption & {
  value: DocumentConverterProjectOutputMode;
};
type DocumentConverterPaperChoice = UiSegmentedToggleOption & {
  value: DocumentConverterProjectPaperSize;
};
type DocumentConverterSingleFileChoice = UiSegmentedToggleOption & {
  value: DocumentConverterSingleFileSource;
};
type DocumentConverterSingleFileOutputChoice = UiSegmentedToggleOption & {
  value: DocumentConverterSingleFileOutput;
};

const workspaceModeOptions: { label: string; value: DocumentConverterWorkspaceMode; dataTest: string }[] = [
  { label: "HTML/CSS-projekt", value: "project_preview", dataTest: "document-converter-mode-project" },
  { label: "Filkonvertering", value: "single_file", dataTest: "document-converter-mode-single" },
];

const singleFileOriginOptions: UiSegmentedToggleOption[] = [
  { label: "Lokal fil", value: "upload", dataTest: "document-converter-origin-upload" },
  { label: "Mina filer", value: "saved_file", dataTest: "document-converter-origin-saved" },
];

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

const sourceLabelMap: Record<DocumentConverterSingleFileSource, string> = {
  docx: "DOCX",
  html: "HTML",
  md: "Markdown",
  pdf: "PDF",
};
const outputLabelMap: Record<DocumentConverterSingleFileOutput, string> = {
  docx: "DOCX",
  md: "Markdown",
  pdf: "PDF",
};

const workspaceMode = ref<DocumentConverterWorkspaceMode>("project_preview");
const project = useDocumentConverterProjectPreview();
const singleFile = useDocumentConverterSingleFile();
const history = useDocumentConverterSessionHistory();

useDocumentConverterHistoryBridge({
  workspaceMode,
  project,
  singleFile,
  history,
});

const singleFileSourceOptions = computed<DocumentConverterSingleFileChoice[]>(() => {
  return singleFile.availableSourceFormats.value.map((value) => ({
    label: sourceLabelMap[value],
    value,
    dataTest: `document-converter-source-${value}`,
  }));
});

const singleFileOutputOptions = computed<DocumentConverterSingleFileOutputChoice[]>(() => {
  return singleFile.availableOutputFormats.value.map((value) => ({
    label: outputLabelMap[value],
    value,
    dataTest: `document-converter-output-${value}`,
  }));
});

const mobileSummaryTitle = computed(() => {
  if (workspaceMode.value === "project_preview") {
    return project.selectedFileLabel();
  }
  return singleFile.selectedSourceName.value;
});

const mobileSummaryDetails = computed(() => {
  if (workspaceMode.value === "project_preview") {
    return [
      `${project.totalProjectFiles.value} filer`,
      `${project.fileSummary.value.html.length} HTML`,
      `${project.fileSummary.value.css.length} CSS`,
      `${project.fileSummary.value.images.length} bilder`,
    ];
  }
  return [
    singleFile.sourceMode.value === "upload" ? "Lokal fil" : "Mina filer",
    sourceLabelMap[singleFile.selectedSourceFormat.value],
    outputLabelMap[singleFile.selectedOutputFormat.value],
  ];
});

const feedbackMessage = computed(() => {
  if (workspaceMode.value === "project_preview") {
    return project.statusMessage.value ?? project.errorMessage.value;
  }
  return singleFile.statusMessage.value ?? singleFile.errorMessage.value;
});

const feedbackIsError = computed(() => {
  if (workspaceMode.value === "project_preview") {
    return Boolean(project.errorMessage.value);
  }
  return Boolean(singleFile.errorMessage.value);
});

const canRetryCurrentMode = computed(() => {
  if (workspaceMode.value === "project_preview") {
    return project.canRetryPreview.value;
  }
  return history.activeEntry.value?.status === "failed" && history.canRetryActiveEntry.value;
});

const isLiveProjectResultSelected = computed(() => {
  return (
    workspaceMode.value === "project_preview" &&
    history.activeEntry.value?.id === project.activePreviewEntryId.value &&
    project.preview.value !== null
  );
});
const resultTitle = computed(() => {
  if (isLiveProjectResultSelected.value) {
    return project.selectedArtifact.value?.filename ?? project.selectedFileLabel();
  }
  return history.activeArtifactFilename.value ?? history.activeEntry.value?.filename ?? "Resultat";
});
const { filenameExtensionLabel, filenameStemIntent } = useDocumentConverterFilenameIntent(resultTitle);
const resultStateLabel = computed(() => {
  const entry = history.activeEntry.value;
  if (!entry) {
    return workspaceMode.value === "single_file"
      ? "Välj en fil som du vill konvertera."
      : "Lägg till HTML, CSS och bilder.";
  }
  if (entry.status === "failed") {
    return entry.errorMessage ?? "Resultatet gick inte att skapa.";
  }
  if (isLiveProjectResultSelected.value ? project.previewPdfUrl.value : history.activePreviewUrl.value) {
    return `${entry.resultTypeLabel} klart för granskning.`;
  }
  return `${entry.resultTypeLabel} klart att ladda ned eller spara.`;
});
const resultPreviewUrl = computed(() => {
  if (isLiveProjectResultSelected.value) {
    return project.previewPdfUrl.value;
  }
  return history.activePreviewUrl.value;
});
const resultArtifactOptions = computed(() => {
  if (isLiveProjectResultSelected.value) {
    return (project.preview.value?.artifacts ?? []).map((artifact) => ({
      artifactId: artifact.artifact_id,
      filename: artifact.filename,
    }));
  }
  return history.artifactOptions.value;
});
const resultActiveArtifactId = computed(() => {
  if (isLiveProjectResultSelected.value) {
    return project.selectedArtifact.value?.artifact_id ?? null;
  }
  return history.activeArtifactId.value;
});
const canDownloadResult = computed(() => {
  if (isLiveProjectResultSelected.value) {
    return project.canUseSelectedArtifact.value;
  }
  return history.canDownloadActiveEntry.value;
});
const canSaveResult = computed(() => {
  if (isLiveProjectResultSelected.value) {
    return project.canUseSelectedArtifact.value;
  }
  return history.canSaveActiveEntry.value;
});

const isDownloadingResult = computed(() => {
  if (isLiveProjectResultSelected.value) {
    return project.isDownloading.value;
  }
  return history.isDownloading.value;
});
const isSavingResult = computed(() => {
  if (isLiveProjectResultSelected.value) {
    return project.isSaving.value;
  }
  return history.isSaving.value;
});

async function startSingleFileConversion(): Promise<void> {
  await singleFile.submitCurrentSelection();
}

async function downloadResult(): Promise<void> {
  if (isLiveProjectResultSelected.value) {
    await project.downloadSelectedArtifact(filenameStemIntent.value);
    return;
  }
  await history.downloadActiveEntry(filenameStemIntent.value);
}

async function retryCurrentMode(): Promise<void> {
  if (workspaceMode.value === "project_preview") {
    await project.retryPreview();
    return;
  }
  await history.retryActiveEntry();
}

async function saveResult(): Promise<void> {
  if (isLiveProjectResultSelected.value) {
    await project.saveSelectedArtifact(filenameStemIntent.value);
    await singleFile.loadSources();
    return;
  }
  await history.saveActiveEntry(filenameStemIntent.value);
}

async function selectResultArtifact(artifactId: string): Promise<void> {
  if (isLiveProjectResultSelected.value) {
    project.selectArtifact(artifactId);
    return;
  }
  await history.selectActiveArtifact(artifactId);
}

</script>

<template>
  <main
    class="dc-workbench"
    aria-label="Dokumentkonverterare"
  >
    <header class="dc-topbar">
      <h1>DOKUMENTKONVERTERARE</h1>
      <nav
        class="dc-mode-tabs"
        role="tablist"
        aria-label="Välj arbetsyta"
      >
        <button
          v-for="option in workspaceModeOptions"
          :key="option.value"
          type="button"
          role="tab"
          class="dc-mode-tab"
          :class="{ 'dc-mode-tab--active': workspaceMode === option.value }"
          :aria-selected="workspaceMode === option.value"
          :data-test="option.dataTest"
          @click="workspaceMode = option.value"
        >
          {{ option.label }}
        </button>
      </nav>
    </header>

    <section
      class="dc-mobile-summary"
      aria-label="Mobilöversikt"
    >
      <div
        class="dc-mobile-project"
        aria-label="Projektöversikt"
      >
        <strong class="dc-mobile-project__title">{{ mobileSummaryTitle }}</strong>
        <span
          v-for="detail in mobileSummaryDetails"
          :key="detail"
        >
          {{ detail }}
        </span>
      </div>
    </section>

    <section class="dc-workspace">
      <section
        class="dc-rail"
        aria-label="Källor"
        data-testid="document-converter-source-column"
      >
        <DocumentConverterSourceIntake
          :workspace-mode="workspaceMode"
          :selected-saved-file-ref="singleFile.selectedSavedFileRef.value"
          :selected-source-accept="singleFile.selectedSourceAccept.value"
          :selected-source-name="singleFile.selectedSourceName.value"
          :source-mode="singleFile.sourceMode.value"
          :source-mode-options="singleFileOriginOptions"
          :saved-files="singleFile.savedFiles.value"
          @project-files-dropped="project.onFilesDropped"
          @project-files-selected="project.onFilesSelected"
          @select-saved-file="singleFile.selectSavedFile"
          @select-single-files="singleFile.selectLocalUploads"
          @select-source-mode="singleFile.setSourceMode"
        />

        <DocumentConverterSourcePanel
          :workspace-mode="workspaceMode"
          :project-css-files="project.fileSummary.value.css"
          :project-html-files="project.fileSummary.value.html"
          :project-image-files="project.fileSummary.value.images"
          :project-selected-html-filename="project.selectedHtmlFile.value?.name ?? null"
          :single-file-mode-label="singleFile.sourceMode.value === 'upload' ? 'Lokal fil' : 'Mina filer'"
          :single-file-source-name="singleFile.selectedSourceName.value"
          :single-file-upload-files="singleFile.selectedUploads.value"
          @move-single-file-upload="singleFile.moveLocalUpload"
          @select-project-html="project.selectedHtmlFilename.value = $event"
        />
      </section>

      <section
        class="dc-controls"
        aria-label="Val för export"
        data-testid="document-converter-operations-column"
      >
        <template v-if="workspaceMode === 'project_preview'">
          <section class="dc-operations-section">
            <div class="dc-control-heading">
              <h2>Utdatainställningar</h2>
            </div>

            <div class="dc-field">
              <span>Exportera som</span>
              <UiSegmentedTileToggle
                :model-value="project.outputMode.value"
                :options="outputChoices"
                aria-label="Exportera som"
                @update:model-value="(value) => project.selectOutputMode(value as DocumentConverterProjectOutputMode)"
              />
            </div>

            <div class="dc-field">
              <span>Format</span>
              <UiSegmentedToggle
                :model-value="project.paperSize.value"
                :options="paperChoices"
                aria-label="Format"
                variant="subrail"
                width="full"
                :columns="3"
                @update:model-value="(value) => project.selectPaperSize(value as DocumentConverterProjectPaperSize)"
              />
            </div>
          </section>
        </template>

        <template v-else>
          <DocumentConverterSingleFileControls
            :selected-output-format="singleFile.selectedOutputFormat.value"
            :selected-source-format="singleFile.selectedSourceFormat.value"
            :is-loading-sources="singleFile.isLoadingSources.value"
            :is-submitting="singleFile.isSubmitting.value"
            :output-options="singleFileOutputOptions"
            :source-options="singleFileSourceOptions"
            @select-output-format="singleFile.setOutputFormat"
            @select-source-format="singleFile.setSourceFormat"
            @submit="startSingleFileConversion"
          />
        </template>

        <DocumentConverterArtifactSelector
          :artifact-options="resultArtifactOptions"
          :active-artifact-id="resultActiveArtifactId"
          @select-artifact="selectResultArtifact"
        />

        <DocumentConverterResultActions
          :action-error-message="history.actionErrorMessage.value"
          :can-download="canDownloadResult"
          :can-retry="canRetryCurrentMode"
          :can-save="canSaveResult"
          :feedback-is-error="feedbackIsError"
          :feedback-message="feedbackMessage"
          :filename-extension="filenameExtensionLabel"
          :filename-stem="filenameStemIntent"
          :is-downloading="isDownloadingResult"
          :is-retry-disabled="project.isPreviewRunning.value || singleFile.isSubmitting.value || history.isRetrying.value"
          :is-saving="isSavingResult"
          :result-state-label="resultStateLabel"
          @download="downloadResult"
          @retry="retryCurrentMode"
          @save="saveResult"
          @update-filename-stem="filenameStemIntent = $event"
        />
      </section>

      <DocumentConverterResultPanel
        :active-preview-url="resultPreviewUrl"
        :result-title="resultTitle"
        :result-state-label="resultStateLabel"
        data-testid="document-converter-preview-column"
      />
    </section>
  </main>
</template>
