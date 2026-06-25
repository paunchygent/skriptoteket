/**
 * Document Converter project-preview route state.
 *
 * Domain purpose:
 *   Orchestrate teacher-selected files, output controls, preview result state,
 *   and explicit download/save/discard actions for the Document Converter app.
 *
 * Relationships:
 *   - Used by `DocumentConverterView.vue`.
 *   - Calls the route-specific project-preview API client.
 *   - Keeps backend identifiers inside action parameters, not visible UI copy.
 */

import { computed, ref } from "vue";

import { triggerBrowserDownload } from "../exam-converter/browserDownload";
import {
  discardDocumentConverterProjectPreview,
  downloadDocumentConverterProjectPreviewArtifact,
  renderDocumentConverterProjectPreview,
  saveDocumentConverterProjectPreviewArtifact,
  type DocumentConverterProjectOutputMode,
  type DocumentConverterProjectPaperSize,
  type DocumentConverterProjectPreviewArtifact,
  type DocumentConverterProjectPreviewResult,
  type DocumentConverterProjectTemplateId,
} from "./documentConverterProjectPreviewApi";
import {
  getDocumentConverterProjectFileKind,
  summarizeDocumentConverterProjectFiles,
} from "./documentConverterProjectFiles";

const PROJECT_FILE_CAPS = {
  html: 10,
  css: 10,
  images: 20,
} as const;

export function useDocumentConverterProjectPreview() {
  const files = ref<File[]>([]);
  const outputMode = ref<DocumentConverterProjectOutputMode>("separate_pdfs");
  const paperSize = ref<DocumentConverterProjectPaperSize>("a4");
  const templateId = ref<DocumentConverterProjectTemplateId>("academic_phd");
  const selectedHtmlFilename = ref<string | null>(null);
  const preview = ref<DocumentConverterProjectPreviewResult | null>(null);
  const selectedArtifactId = ref<string | null>(null);
  const isPreviewRunning = ref(false);
  const isDownloading = ref(false);
  const isSaving = ref(false);
  const isDiscarding = ref(false);
  const isPreviewStale = ref(false);
  const errorMessage = ref<string | null>(null);

  const fileSummary = computed(() => summarizeDocumentConverterProjectFiles(files.value));
  const selectedHtmlFile = computed(() => {
    return (
      fileSummary.value.html.find((file) => file.name === selectedHtmlFilename.value) ??
      fileSummary.value.html[0] ??
      null
    );
  });
  const selectedArtifact = computed<DocumentConverterProjectPreviewArtifact | null>(() => {
    if (!preview.value) {
      return null;
    }
    return (
      preview.value.artifacts.find((artifact) => artifact.artifact_id === selectedArtifactId.value) ??
      preview.value.artifacts[0] ??
      null
    );
  });
  const previewActionLabel = computed(() => {
    if (isPreviewRunning.value) {
      return "Förhandsvisar...";
    }
    return preview.value && isPreviewStale.value ? "Uppdatera" : "Förhandsvisa";
  });
  const totalProjectFiles = computed(() => files.value.length);
  const canPreview = computed(() => Boolean(selectedHtmlFile.value) && !isPreviewRunning.value);

  function mergeProjectFiles(existingFiles: readonly File[], nextFiles: readonly File[]): File[] {
    const merged = new Map<string, File>();
    for (const file of [...existingFiles, ...nextFiles]) {
      merged.set(file.name, file);
    }
    return Array.from(merged.values());
  }

  function validateProjectFiles(candidateFiles: readonly File[]): string | null {
    if (candidateFiles.some((file) => getDocumentConverterProjectFileKind(file.name) === "other")) {
      return "Filen stöds inte. Lägg till HTML, CSS eller bilder.";
    }

    const summary = summarizeDocumentConverterProjectFiles(candidateFiles);
    if (summary.html.length > PROJECT_FILE_CAPS.html) {
      return "Du kan lägga till högst 10 HTML-filer.";
    }
    if (summary.css.length > PROJECT_FILE_CAPS.css) {
      return "Du kan lägga till högst 10 CSS-filer.";
    }
    if (summary.images.length > PROJECT_FILE_CAPS.images) {
      return "Du kan lägga till högst 20 bilder.";
    }
    return null;
  }

  function markPreviewStale(): void {
    errorMessage.value = null;
    if (preview.value) {
      isPreviewStale.value = true;
    }
  }

  function onFilesSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const selectedFiles = Array.from(input.files ?? []);
    const candidateFiles = mergeProjectFiles(files.value, selectedFiles);
    const validationError = validateProjectFiles(candidateFiles);
    input.value = "";
    if (validationError) {
      errorMessage.value = validationError;
      return;
    }

    files.value = candidateFiles;
    if (!selectedHtmlFilename.value || !selectedHtmlFile.value) {
      selectedHtmlFilename.value = fileSummary.value.html[0]?.name ?? null;
    }
    markPreviewStale();
  }

  function selectOutputMode(nextOutputMode: DocumentConverterProjectOutputMode): void {
    outputMode.value = nextOutputMode;
    markPreviewStale();
  }

  function selectPaperSize(nextPaperSize: DocumentConverterProjectPaperSize): void {
    paperSize.value = nextPaperSize;
    markPreviewStale();
  }

  function selectedFileLabel(): string {
    return selectedHtmlFile.value?.name ?? "HTML/CSS";
  }

  async function previewProject(): Promise<void> {
    if (!selectedHtmlFile.value) {
      errorMessage.value = "Det gick inte att förhandsvisa. Lägg till en HTML-fil.";
      return;
    }
    isPreviewRunning.value = true;
    errorMessage.value = null;
    const previousPreview = preview.value;
    try {
      const result = await renderDocumentConverterProjectPreview({
        files: files.value,
        htmlEntryFilename: selectedHtmlFile.value.name,
        outputMode: outputMode.value,
        paperSize: paperSize.value,
        templateId: templateId.value,
      });
      if (result.status === "failed" || result.artifacts.length === 0) {
        throw new Error("Preview failed");
      }
      preview.value = result;
      selectedArtifactId.value = result.artifacts[0]?.artifact_id ?? null;
      isPreviewStale.value = false;
    } catch {
      if (!previousPreview) {
        preview.value = null;
        selectedArtifactId.value = null;
        isPreviewStale.value = false;
      } else {
        isPreviewStale.value = true;
      }
      errorMessage.value = "Det gick inte att förhandsvisa. Försök igen.";
    } finally {
      isPreviewRunning.value = false;
    }
  }

  async function downloadSelectedArtifact(): Promise<void> {
    if (!preview.value || !selectedArtifact.value) {
      return;
    }
    isDownloading.value = true;
    errorMessage.value = null;
    try {
      const response = await downloadDocumentConverterProjectPreviewArtifact({
        previewId: preview.value.preview_id,
        artifact: selectedArtifact.value,
      });
      triggerBrowserDownload(response.blob, response.filename ?? selectedArtifact.value.filename);
    } catch {
      errorMessage.value = "Det gick inte att ladda ned. Försök igen.";
    } finally {
      isDownloading.value = false;
    }
  }

  async function saveSelectedArtifact(): Promise<void> {
    if (!preview.value || !selectedArtifact.value) {
      return;
    }
    isSaving.value = true;
    errorMessage.value = null;
    try {
      await saveDocumentConverterProjectPreviewArtifact({
        previewId: preview.value.preview_id,
        artifact: selectedArtifact.value,
      });
    } catch {
      errorMessage.value = "Det gick inte att spara. Försök igen.";
    } finally {
      isSaving.value = false;
    }
  }

  async function discardPreview(): Promise<void> {
    if (!preview.value) {
      return;
    }
    isDiscarding.value = true;
    errorMessage.value = null;
    try {
      await discardDocumentConverterProjectPreview({ previewId: preview.value.preview_id });
      preview.value = null;
      selectedArtifactId.value = null;
      isPreviewStale.value = false;
    } catch {
      errorMessage.value = "Det gick inte att ta bort. Försök igen.";
    } finally {
      isDiscarding.value = false;
    }
  }

  return {
    canPreview,
    discardPreview,
    downloadSelectedArtifact,
    errorMessage,
    fileSummary,
    isDiscarding,
    isDownloading,
    isPreviewRunning,
    isPreviewStale,
    isSaving,
    markPreviewStale,
    onFilesSelected,
    outputMode,
    paperSize,
    preview,
    previewActionLabel,
    previewProject,
    saveSelectedArtifact,
    selectOutputMode,
    selectPaperSize,
    selectedArtifact,
    selectedArtifactId,
    selectedFileLabel,
    selectedHtmlFile,
    selectedHtmlFilename,
    templateId,
    totalProjectFiles,
  };
}
