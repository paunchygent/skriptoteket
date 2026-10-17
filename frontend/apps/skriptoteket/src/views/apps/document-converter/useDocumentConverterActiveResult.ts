/**
 * Document Converter active-result presentation and actions.
 *
 * Domain purpose:
 *   Select the live project or route-session result, keep its editable filename
 *   intent aligned, and dispatch artifact selection, download, and save actions.
 *
 * Relationships:
 *   - Used by `DocumentConverterView.vue` for both workspace modes.
 *   - Reads project-preview and session-history state without owning their
 *     lifecycles, workspace feedback, or retry behavior.
 */

import { computed, type ComputedRef, type Ref } from "vue";

import { useDocumentConverterFilenameIntent } from "./useDocumentConverterFilenameIntent";
import type { useDocumentConverterProjectPreview } from "./useDocumentConverterProjectPreview";
import type { useDocumentConverterSessionHistory } from "./useDocumentConverterSessionHistory";
import type { useDocumentConverterSingleFile } from "./useDocumentConverterSingleFile";

type WorkspaceMode = "project_preview" | "single_file";

export function useDocumentConverterActiveResult(args: {
  workspaceMode: Ref<WorkspaceMode>;
  project: ReturnType<typeof useDocumentConverterProjectPreview>;
  singleFile: ReturnType<typeof useDocumentConverterSingleFile>;
  projectHistory: ReturnType<typeof useDocumentConverterSessionHistory>;
  activeHistory: ComputedRef<ReturnType<typeof useDocumentConverterSessionHistory>>;
  isCurrentProjectPreviewFailure: ComputedRef<boolean>;
  isRetainedProjectPreviewVisible: ComputedRef<boolean>;
}) {
  const {
    workspaceMode,
    project,
    singleFile,
    projectHistory,
    activeHistory,
    isCurrentProjectPreviewFailure,
    isRetainedProjectPreviewVisible,
  } = args;

  const isLiveProjectResultSelected = computed(() => {
    return (
      workspaceMode.value === "project_preview" &&
      !isCurrentProjectPreviewFailure.value &&
      projectHistory.activeEntry.value?.id === project.activePreviewEntryId.value &&
      project.preview.value !== null
    );
  });
  const resultFilename = computed<string | null>(() => {
    if (isLiveProjectResultSelected.value) {
      return project.selectedArtifact.value?.filename ?? project.selectedFileLabel();
    }
    return activeHistory.value.activeArtifactFilename.value ?? activeHistory.value.activeEntry.value?.filename ?? null;
  });
  const resultTitle = computed(() => resultFilename.value ?? "Resultat");
  const { filenameExtensionLabel, filenameStemIntent } = useDocumentConverterFilenameIntent(resultFilename);
  const resultStateLabel = computed(() => {
    const entry = activeHistory.value.activeEntry.value;
    if (isRetainedProjectPreviewVisible.value) {
      return "Visar föregående PDF.";
    }
    if (isCurrentProjectPreviewFailure.value) {
      return project.errorMessage.value ?? "Resultatet gick inte att skapa.";
    }
    if (!entry) {
      return workspaceMode.value === "single_file"
        ? "Välj en fil som du vill konvertera."
        : "Lägg till HTML, CSS och bilder.";
    }
    if (entry.status === "failed") {
      return entry.errorMessage ?? "Resultatet gick inte att skapa.";
    }
    if (isLiveProjectResultSelected.value ? project.previewPdfUrl.value : activeHistory.value.activePreviewUrl.value) {
      return `${entry.resultTypeLabel} klart för granskning.`;
    }
    return `${entry.resultTypeLabel} klart att ladda ned eller spara.`;
  });
  const resultPreviewUrl = computed(() => {
    if (isLiveProjectResultSelected.value) {
      return project.previewPdfUrl.value;
    }
    return activeHistory.value.activePreviewUrl.value;
  });
  const resultArtifactOptions = computed(() => {
    if (isCurrentProjectPreviewFailure.value) {
      return [];
    }
    if (isLiveProjectResultSelected.value) {
      return (project.preview.value?.artifacts ?? []).map((artifact) => ({
        artifactId: artifact.artifact_id,
        filename: artifact.filename,
      }));
    }
    return activeHistory.value.artifactOptions.value;
  });
  const resultActiveArtifactId = computed(() => {
    if (isCurrentProjectPreviewFailure.value) {
      return null;
    }
    if (isLiveProjectResultSelected.value) {
      return project.selectedArtifact.value?.artifact_id ?? null;
    }
    return activeHistory.value.activeArtifactId.value;
  });
  const canDownloadResult = computed(() => {
    if (isCurrentProjectPreviewFailure.value) {
      return false;
    }
    if (isLiveProjectResultSelected.value) {
      return project.canUseSelectedArtifact.value;
    }
    return activeHistory.value.canDownloadActiveEntry.value;
  });
  const canSaveResult = computed(() => {
    if (isCurrentProjectPreviewFailure.value) {
      return false;
    }
    if (isLiveProjectResultSelected.value) {
      return project.canUseSelectedArtifact.value;
    }
    return activeHistory.value.canSaveActiveEntry.value;
  });

  const isDownloadingResult = computed(() => {
    if (isLiveProjectResultSelected.value) {
      return project.isDownloading.value;
    }
    return activeHistory.value.isDownloading.value;
  });
  const isSavingResult = computed(() => {
    if (isLiveProjectResultSelected.value) {
      return project.isSaving.value;
    }
    return activeHistory.value.isSaving.value;
  });

  const actionErrorMessage = computed(() => activeHistory.value.actionErrorMessage.value);

  async function downloadResult(): Promise<void> {
    if (isCurrentProjectPreviewFailure.value) {
      return;
    }
    if (isLiveProjectResultSelected.value) {
      await project.downloadSelectedArtifact(filenameStemIntent.value);
      return;
    }
    await activeHistory.value.downloadActiveEntry(filenameStemIntent.value);
  }

  async function saveResult(): Promise<void> {
    if (isCurrentProjectPreviewFailure.value) {
      return;
    }
    if (isLiveProjectResultSelected.value) {
      await project.saveSelectedArtifact(filenameStemIntent.value);
      await singleFile.loadSources();
      return;
    }
    await activeHistory.value.saveActiveEntry(filenameStemIntent.value);
  }

  async function selectResultArtifact(artifactId: string): Promise<void> {
    if (isCurrentProjectPreviewFailure.value) {
      return;
    }
    if (isLiveProjectResultSelected.value) {
      project.selectArtifact(artifactId);
      return;
    }
    await activeHistory.value.selectActiveArtifact(artifactId);
  }

  return {
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
  };
}
