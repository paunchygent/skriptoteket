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
import { useDocumentConverterActiveResult } from "./useDocumentConverterActiveResult";
import { useDocumentConverterProjectPreview } from "./useDocumentConverterProjectPreview";
import { useDocumentConverterHistoryBridge } from "./useDocumentConverterHistoryBridge";
import { useDocumentConverterSessionHistory } from "./useDocumentConverterSessionHistory";
import {
  useDocumentConverterSingleFile,
  type DocumentConverterSingleFileOutput,
  type DocumentConverterSingleFileSource,
} from "./useDocumentConverterSingleFile";
import {
  OUTPUT_LABELS,
  SOURCE_LABELS,
} from "./documentConverterSingleFileSelection";

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

const workspaceMode = ref<DocumentConverterWorkspaceMode>("project_preview");
const project = useDocumentConverterProjectPreview();
const singleFile = useDocumentConverterSingleFile();
const projectHistory = useDocumentConverterSessionHistory();
const singleFileHistory = useDocumentConverterSessionHistory();
const activeHistory = computed(() => (
  workspaceMode.value === "project_preview" ? projectHistory : singleFileHistory
));

useDocumentConverterHistoryBridge({
  workspaceMode,
  project,
  singleFile,
  projectHistory,
  singleFileHistory,
});

const singleFileSourceOptions = computed<DocumentConverterSingleFileChoice[]>(() => {
  return singleFile.availableSourceFormats.value.map((value) => ({
    label: SOURCE_LABELS[value],
    value,
    dataTest: `document-converter-source-${value}`,
  }));
});

const singleFileOutputOptions = computed<DocumentConverterSingleFileOutputChoice[]>(() => {
  return singleFile.availableOutputFormats.value.map((value) => ({
    label: OUTPUT_LABELS[value],
    value,
    dataTest: `document-converter-output-${value}`,
  }));
});

const mobileSummaryTitle = computed(() => singleFile.selectedSourceName.value);

const mobileSummaryDetails = computed(() => [
  singleFile.sourceMode.value === "upload" ? "Lokal fil" : "Mina filer",
  SOURCE_LABELS[singleFile.selectedSourceFormat.value],
  OUTPUT_LABELS[singleFile.selectedOutputFormat.value],
]);

const isCurrentProjectPreviewFailure = computed(() => {
  return workspaceMode.value === "project_preview" && project.canRetryPreview.value && Boolean(project.errorMessage.value);
});
const isRetainedProjectPreviewVisible = computed(() => {
  return isCurrentProjectPreviewFailure.value && Boolean(project.previewPdfUrl.value || projectHistory.activePreviewUrl.value);
});

const feedback = computed(() => {
  const current = workspaceMode.value === "project_preview" ? project : singleFile;
  const errorMessage = current.errorMessage.value;
  if (errorMessage) {
    return {
      message: isRetainedProjectPreviewVisible.value
        ? `${errorMessage} Försök igen för att skapa en ny PDF.`
        : errorMessage,
      isError: true,
    };
  }
  return { message: current.statusMessage.value, isError: false };
});

const canRetryCurrentMode = computed(() => {
  if (workspaceMode.value === "project_preview") {
    return project.canRetryPreview.value;
  }
  return singleFileHistory.activeEntry.value?.status === "failed" && singleFileHistory.canRetryActiveEntry.value;
});

const {
  actionErrorMessage,
  canDownloadResult,
  canSaveResult,
  downloadResult,
  filenameExtensionLabel,
  filenameStemIntent,
  isDownloadingResult,
  isSavingResult,
  resultActiveArtifactId,
  resultArtifactOptions,
  resultPreviewUrl,
  resultStateLabel,
  resultTitle,
  saveResult,
  selectResultArtifact,
} = useDocumentConverterActiveResult({
  workspaceMode,
  project,
  singleFile,
  projectHistory,
  activeHistory,
  isCurrentProjectPreviewFailure,
  isRetainedProjectPreviewVisible,
});
const isRetryDisabled = computed(() => (
  project.isPreviewRunning.value ||
  singleFile.isSubmitting.value ||
  activeHistory.value.isRetrying.value
));

async function startSingleFileConversion(): Promise<void> {
  await singleFile.submitCurrentSelection();
}

function selectWorkspaceMode(nextMode: DocumentConverterWorkspaceMode): void {
  workspaceMode.value = nextMode;
}

async function retryCurrentMode(): Promise<void> {
  if (workspaceMode.value === "project_preview") {
    await project.retryPreview();
    return;
  }
  await activeHistory.value.retryActiveEntry();
}

</script>

<template>
  <main
    class="dc-workbench"
    :class="{ 'dc-workbench--single-file': workspaceMode === 'single_file' }"
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
          @click="selectWorkspaceMode(option.value)"
        >
          {{ option.label }}
        </button>
      </nav>
    </header>

    <section
      v-if="workspaceMode === 'single_file'"
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
        <header class="dc-column-header">
          <h2 data-testid="document-converter-source-column-title">
            Källa
          </h2>
        </header>

        <DocumentConverterSourceIntake
          :workspace-mode="workspaceMode"
          :selected-saved-file-ref="null"
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
          :single-file-saved-files="singleFile.selectedSavedFiles.value"
          :single-file-mode-label="singleFile.sourceMode.value === 'upload' ? 'Lokal fil' : 'Mina filer'"
          :single-file-source-name="singleFile.selectedSourceName.value"
          :single-file-upload-files="singleFile.selectedUploads.value"
          @move-single-file-saved-file="singleFile.moveSavedFile"
          @move-single-file-upload="singleFile.moveLocalUpload"
          @remove-single-file-saved-file="singleFile.removeSavedFile"
          @remove-single-file-upload="singleFile.removeLocalUpload"
          @select-project-html="project.selectedHtmlFilename.value = $event"
        />
      </section>

      <section
        class="dc-controls"
        aria-label="Val för export"
        data-testid="document-converter-operations-column"
      >
        <header class="dc-column-header">
          <h2 data-testid="document-converter-operations-column-title">
            Konvertering
          </h2>
        </header>

        <template v-if="workspaceMode === 'project_preview'">
          <section class="dc-operations-section">
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
          :action-error-message="actionErrorMessage"
          :can-download="canDownloadResult"
          :can-retry="canRetryCurrentMode"
          :can-save="canSaveResult"
          :feedback-is-error="feedback.isError"
          :feedback-message="feedback.message"
          :filename-extension="filenameExtensionLabel"
          :filename-stem="filenameStemIntent"
          :is-downloading="isDownloadingResult"
          :is-retry-disabled="isRetryDisabled"
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
