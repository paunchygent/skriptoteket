/**
 * Document Converter project-preview route state.
 *
 * Domain purpose:
 *   Orchestrate teacher-selected files, governed export controls, automatic
 *   PDF preview refresh, and current-artifact download/save actions for the
 *   Document Converter app.
 *
 * Relationships:
 *   - Used by `DocumentConverterView.vue`.
 *   - Calls the route-specific project-preview API client.
 *   - Keeps backend identifiers inside action parameters, not visible UI copy.
 */

import { computed, onScopeDispose, ref, watch } from "vue";

import { triggerBrowserDownload } from "../exam-converter/browserDownload";
import {
  downloadDocumentConverterProjectPreviewArtifact,
  loadDocumentConverterProjectPreviewArtifactBlob,
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

const AUTO_PREVIEW_DEBOUNCE_MS = 350;
const PREVIEW_FAILURE_MESSAGE = "Det gick inte att skapa PDF:en.";

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
  const previewPdfUrl = ref<string | null>(null);
  const previewPdfArtifactId = ref<string | null>(null);
  const isPreviewRunning = ref(false);
  const isArtifactPreviewLoading = ref(false);
  const isDownloading = ref(false);
  const isSaving = ref(false);
  const errorMessage = ref<string | null>(null);
  const canRetryPreview = ref(false);
  const latestSuccessfulSelectionKey = ref<string | null>(null);

  let autoPreviewTimeout: number | null = null;
  let previewRequestSequence = 0;
  let artifactPreviewRequestSequence = 0;

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
  const totalProjectFiles = computed(() => files.value.length);
  const currentSelectionKey = computed(() => {
    if (!selectedHtmlFile.value) {
      return null;
    }
    return JSON.stringify({
      files: files.value.map((file) => ({
        lastModified: file.lastModified,
        name: file.name,
        size: file.size,
        type: file.type,
      })),
      htmlEntryFilename: selectedHtmlFile.value.name,
      outputMode: outputMode.value,
      paperSize: paperSize.value,
      templateId: templateId.value,
    });
  });
  const isCurrentPreviewReady = computed(() => {
    return Boolean(
      selectedArtifact.value &&
        previewPdfUrl.value &&
        previewPdfArtifactId.value === selectedArtifact.value.artifact_id &&
        currentSelectionKey.value &&
        latestSuccessfulSelectionKey.value === currentSelectionKey.value &&
        !isPreviewRunning.value &&
        !isArtifactPreviewLoading.value,
    );
  });
  const statusMessage = computed(() => {
    if (isPreviewRunning.value) {
      return "Skapar PDF...";
    }
    return null;
  });

  function setMessage(message: string | null, options?: { retryable?: boolean }): void {
    errorMessage.value = message;
    canRetryPreview.value = options?.retryable ?? false;
  }

  function replacePreviewPdfUrl(nextUrl: string | null): void {
    if (previewPdfUrl.value && previewPdfUrl.value !== nextUrl) {
      URL.revokeObjectURL(previewPdfUrl.value);
    }
    previewPdfUrl.value = nextUrl;
  }

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

  function selectOutputMode(nextOutputMode: DocumentConverterProjectOutputMode): void {
    outputMode.value = nextOutputMode;
  }

  function selectPaperSize(nextPaperSize: DocumentConverterProjectPaperSize): void {
    paperSize.value = nextPaperSize;
  }

  function selectArtifact(nextArtifactId: string): void {
    selectedArtifactId.value = nextArtifactId;
    setMessage(null);
  }

  function selectedFileLabel(): string {
    return selectedHtmlFile.value?.name ?? "HTML/CSS";
  }

  function acceptProjectFiles(nextFiles: readonly File[]): void {
    const candidateFiles = mergeProjectFiles(files.value, nextFiles);
    const validationError = validateProjectFiles(candidateFiles);
    if (validationError) {
      setMessage(validationError);
      return;
    }

    files.value = candidateFiles;
    if (!selectedHtmlFilename.value || !selectedHtmlFile.value) {
      selectedHtmlFilename.value = summarizeDocumentConverterProjectFiles(candidateFiles).html[0]?.name ?? null;
    }
    setMessage(null);
  }

  function onFilesSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    acceptProjectFiles(Array.from(input.files ?? []));
    input.value = "";
  }

  function onFilesDropped(event: DragEvent): void {
    event.preventDefault();
    acceptProjectFiles(Array.from(event.dataTransfer?.files ?? []));
  }

  function renderParams() {
    if (!selectedHtmlFile.value) {
      return null;
    }
    return {
      files: files.value,
      htmlEntryFilename: selectedHtmlFile.value.name,
      outputMode: outputMode.value,
      paperSize: paperSize.value,
      templateId: templateId.value,
    };
  }

  async function refreshPreview(selectionKey: string): Promise<void> {
    const params = renderParams();
    if (!params || currentSelectionKey.value !== selectionKey) {
      return;
    }

    const requestId = ++previewRequestSequence;
    isPreviewRunning.value = true;
    setMessage(null);
    try {
      const result = await renderDocumentConverterProjectPreview(params);
      if (requestId !== previewRequestSequence || currentSelectionKey.value !== selectionKey) {
        return;
      }

      const defaultArtifact = result.artifacts[0];
      if (result.status === "failed" || !defaultArtifact) {
        throw new Error("Document Converter preview failed");
      }

      const response = await loadDocumentConverterProjectPreviewArtifactBlob({
        previewId: result.preview_id,
        artifact: defaultArtifact,
      });
      if (requestId !== previewRequestSequence || currentSelectionKey.value !== selectionKey) {
        return;
      }

      preview.value = result;
      selectedArtifactId.value = defaultArtifact.artifact_id;
      previewPdfArtifactId.value = defaultArtifact.artifact_id;
      replacePreviewPdfUrl(URL.createObjectURL(response.blob));
      latestSuccessfulSelectionKey.value = selectionKey;
      setMessage(null);
    } catch {
      if (requestId !== previewRequestSequence) {
        return;
      }
      setMessage(PREVIEW_FAILURE_MESSAGE, { retryable: true });
    } finally {
      if (requestId === previewRequestSequence) {
        isPreviewRunning.value = false;
      }
    }
  }

  async function retryPreview(): Promise<void> {
    if (!currentSelectionKey.value || isPreviewRunning.value) {
      return;
    }
    await refreshPreview(currentSelectionKey.value);
  }

  async function downloadSelectedArtifact(): Promise<void> {
    if (!preview.value || !selectedArtifact.value || !isCurrentPreviewReady.value) {
      return;
    }
    isDownloading.value = true;
    setMessage(null);
    try {
      const response = await downloadDocumentConverterProjectPreviewArtifact({
        previewId: preview.value.preview_id,
        artifact: selectedArtifact.value,
      });
      triggerBrowserDownload(response.blob, response.filename ?? selectedArtifact.value.filename);
    } catch {
      setMessage("Det gick inte att ladda ned. Försök igen.");
    } finally {
      isDownloading.value = false;
    }
  }

  async function saveSelectedArtifact(): Promise<void> {
    if (!preview.value || !selectedArtifact.value || !isCurrentPreviewReady.value) {
      return;
    }
    isSaving.value = true;
    setMessage(null);
    try {
      await saveDocumentConverterProjectPreviewArtifact({
        previewId: preview.value.preview_id,
        artifact: selectedArtifact.value,
      });
    } catch {
      setMessage("Det gick inte att spara. Försök igen.");
    } finally {
      isSaving.value = false;
    }
  }

  watch(
    [files, selectedHtmlFilename, outputMode, paperSize, templateId],
    (_, __, onCleanup) => {
      const selectionKey = currentSelectionKey.value;
      if (!selectionKey) {
        return;
      }

      setMessage(null);
      const timeoutId = window.setTimeout(() => {
        if (autoPreviewTimeout === timeoutId) {
          autoPreviewTimeout = null;
        }
        void refreshPreview(selectionKey);
      }, AUTO_PREVIEW_DEBOUNCE_MS);
      autoPreviewTimeout = timeoutId;

      onCleanup(() => {
        window.clearTimeout(timeoutId);
        if (autoPreviewTimeout === timeoutId) {
          autoPreviewTimeout = null;
        }
      });
    },
  );

  watch(
    () => {
      if (!preview.value || !selectedArtifact.value) {
        return null;
      }
      return {
        artifactId: selectedArtifact.value.artifact_id,
        previewId: preview.value.preview_id,
      };
    },
    (next, _, onCleanup) => {
      if (!next || (previewPdfUrl.value && previewPdfArtifactId.value === next.artifactId)) {
        return;
      }

      let isCancelled = false;
      const requestId = ++artifactPreviewRequestSequence;
      isArtifactPreviewLoading.value = true;
      onCleanup(() => {
        isCancelled = true;
      });

      void (async () => {
        try {
          const currentArtifact = selectedArtifact.value;
          if (!currentArtifact) {
            return;
          }

          const response = await loadDocumentConverterProjectPreviewArtifactBlob({
            previewId: next.previewId,
            artifact: currentArtifact,
          });
          if (
            isCancelled ||
            requestId !== artifactPreviewRequestSequence ||
            preview.value?.preview_id !== next.previewId ||
            selectedArtifact.value?.artifact_id !== next.artifactId
          ) {
            return;
          }

          previewPdfArtifactId.value = next.artifactId;
          replacePreviewPdfUrl(URL.createObjectURL(response.blob));
        } catch {
          if (isCancelled || requestId !== artifactPreviewRequestSequence) {
            return;
          }
          setMessage(PREVIEW_FAILURE_MESSAGE, { retryable: true });
        } finally {
          if (!isCancelled && requestId === artifactPreviewRequestSequence) {
            isArtifactPreviewLoading.value = false;
          }
        }
      })();
    },
    { flush: "post" },
  );

  onScopeDispose(() => {
    if (autoPreviewTimeout !== null) {
      window.clearTimeout(autoPreviewTimeout);
      autoPreviewTimeout = null;
    }
    replacePreviewPdfUrl(null);
  });

  return {
    canRetryPreview,
    downloadSelectedArtifact,
    errorMessage,
    fileSummary,
    isCurrentPreviewReady,
    isDownloading,
    isPreviewRunning,
    isSaving,
    onFilesSelected,
    onFilesDropped,
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
    selectedArtifactId,
    selectedFileLabel,
    selectedHtmlFile,
    selectedHtmlFilename,
    statusMessage,
    totalProjectFiles,
  };
}
