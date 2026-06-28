/**
 * Document Converter single-file route state.
 *
 * Domain purpose:
 *   Manage owner-scoped local-upload batches and Mina filer file conversions,
 *   including route selection, result polling, and teacher-facing retry
 *   payloads for the current route session.
 *
 * Relationships:
 *   - Consumed by `DocumentConverterView.vue`.
 *   - Uses `documentConverterFileApi.ts` for backend calls.
 *   - Sends completed outcomes into the route-session history surface.
 */

import { computed, onMounted, ref } from "vue";

import {
  listDocumentConverterSavedFiles,
  listDocumentConverterSingleFileRoutes,
  type DocumentConverterSavedFileSource,
  type DocumentConverterSingleFileRoute,
} from "./documentConverterFileApi";
import {
  isSingleFileSource,
  moveListItem,
  outputFormatsForSource,
  removeListItem,
  sourceAcceptForFormats,
  sourceBatchLabel,
  sourceFormatFromFilename,
  type DocumentConverterSingleFileOutput,
  type DocumentConverterSingleFileSource,
} from "./documentConverterSingleFileSelection";
import {
  submitDocumentConverterSingleFileRequest,
  type DocumentConverterSingleFileOutcome,
  type DocumentConverterSingleFileRequest,
} from "./documentConverterSingleFileSubmission";

export type {
  DocumentConverterSingleFileOutput,
  DocumentConverterSingleFileSource,
} from "./documentConverterSingleFileSelection";

export type DocumentConverterSingleFileSourceMode = "upload" | "saved_file";

export function useDocumentConverterSingleFile() {
  const routes = ref<DocumentConverterSingleFileRoute[]>([]);
  const savedFiles = ref<DocumentConverterSavedFileSource[]>([]);
  const selectedSourceFormat = ref<DocumentConverterSingleFileSource>("html");
  const selectedOutputFormat = ref<DocumentConverterSingleFileOutput>("pdf");
  const sourceMode = ref<DocumentConverterSingleFileSourceMode>("upload");
  const selectedUploads = ref<File[]>([]);
  const selectedSavedFileRefs = ref<string[]>([]);
  const isLoadingSources = ref(false);
  const isSubmitting = ref(false);
  const errorMessage = ref<string | null>(null);
  const statusMessage = ref<string | null>(null);
  const latestOutcome = ref<DocumentConverterSingleFileOutcome | null>(null);

  const availableSourceFormats = computed<DocumentConverterSingleFileSource[]>(() => {
    const uniqueValues = Array.from(new Set(routes.value.map((route) => route.source_format)));
    return uniqueValues.filter(isSingleFileSource);
  });
  const availableOutputFormats = computed<DocumentConverterSingleFileOutput[]>(() => {
    return outputFormatsForSource(routes.value, selectedSourceFormat.value);
  });
  const selectedSavedFiles = computed(() => {
    return selectedSavedFileRefs.value.flatMap((refValue) => {
      const savedFile = savedFiles.value.find((file) => file.ref === refValue);
      return savedFile ? [savedFile] : [];
    });
  });
  const selectedSourceName = computed(() => {
    return sourceMode.value === "upload"
      ? sourceBatchLabel(selectedUploads.value)
      : sourceBatchLabel(selectedSavedFiles.value);
  });
  const selectedSourceAccept = computed(() => {
    return sourceAcceptForFormats(availableSourceFormats.value.length > 0
      ? availableSourceFormats.value
      : [selectedSourceFormat.value]);
  });

  async function loadSources(): Promise<void> {
    isLoadingSources.value = true;
    errorMessage.value = null;
    try {
      const [routesResponse, savedFilesResponse] = await Promise.all([
        listDocumentConverterSingleFileRoutes(),
        listDocumentConverterSavedFiles(),
      ]);
      routes.value = routesResponse.routes ?? [];
      savedFiles.value = savedFilesResponse.files ?? [];

      const availableSources = availableSourceFormats.value;
      if (availableSources.length > 0 && !availableSources.includes(selectedSourceFormat.value)) {
        selectedSourceFormat.value = availableSources[0];
      }
      ensureOutputFormatForSource(selectedSourceFormat.value);
      selectedSavedFileRefs.value = selectedSavedFileRefs.value.filter((refValue) =>
        savedFiles.value.some((file) => file.ref === refValue));
    } catch {
      errorMessage.value = "Det gick inte att ladda filkällorna.";
    } finally {
      isLoadingSources.value = false;
    }
  }

  function setSourceMode(nextMode: DocumentConverterSingleFileSourceMode): void {
    sourceMode.value = nextMode;
    errorMessage.value = null;
  }

  function ensureOutputFormatForSource(nextSourceFormat: DocumentConverterSingleFileSource): void {
    const nextOutputFormats = outputFormatsForSource(routes.value, nextSourceFormat);
    if (!nextOutputFormats.includes(selectedOutputFormat.value)) {
      selectedOutputFormat.value = nextOutputFormats[0] ?? "pdf";
    }
  }

  function setSourceFormat(nextFormat: DocumentConverterSingleFileSource): void {
    selectedSourceFormat.value = nextFormat;
    ensureOutputFormatForSource(nextFormat);
    errorMessage.value = null;
  }

  function setOutputFormat(nextFormat: DocumentConverterSingleFileOutput): void {
    selectedOutputFormat.value = nextFormat;
    errorMessage.value = null;
  }

  function selectLocalUploads(files: File[]): void {
    const nextUploads = files.slice(0, 10);
    const inferredUploadFormats = nextUploads.map((file) => sourceFormatFromFilename(file.name));
    if (inferredUploadFormats.some((format) => format === null)) {
      selectedUploads.value = [];
      errorMessage.value = "Filformatet stöds inte. Välj HTML, DOCX, Markdown eller PDF.";
      return;
    }
    const inferredFormats = new Set(inferredUploadFormats);
    if (inferredFormats.size > 1) {
      selectedUploads.value = [];
      errorMessage.value = "Välj filer med samma källformat.";
      return;
    }
    const inferredFormat = Array.from(inferredFormats)[0] ?? null;
    if (inferredFormat) {
      if (!availableSourceFormats.value.includes(inferredFormat)) {
        selectedUploads.value = [];
        errorMessage.value = "Filformatet stöds inte för den här konverteringen.";
        return;
      }
      selectedSourceFormat.value = inferredFormat;
      ensureOutputFormatForSource(inferredFormat);
    }
    selectedUploads.value = nextUploads;
    errorMessage.value = null;
  }

  function removeLocalUpload(index: number): void {
    const nextUploads = removeListItem(selectedUploads.value, index);
    if (nextUploads) {
      selectedUploads.value = nextUploads;
      errorMessage.value = null;
    }
  }

  function moveLocalUpload(fromIndex: number, toIndex: number): void {
    const nextUploads = moveListItem(selectedUploads.value, fromIndex, toIndex);
    if (nextUploads) {
      selectedUploads.value = nextUploads;
      errorMessage.value = null;
    }
  }

  function selectSavedFile(refValue: string | null): void {
    if (!refValue) {
      return;
    }
    const nextSavedFile = savedFiles.value.find((file) => file.ref === refValue);
    if (!nextSavedFile || !isSingleFileSource(nextSavedFile.source_format)) {
      errorMessage.value = "Filformatet stöds inte. Välj HTML, DOCX, Markdown eller PDF.";
      return;
    }
    if (selectedSavedFileRefs.value.includes(refValue)) {
      errorMessage.value = "Filen är redan vald.";
      return;
    }
    if (selectedSavedFileRefs.value.length >= 10) {
      errorMessage.value = "Du kan konvertera högst 10 filer åt gången.";
      return;
    }
    const selectedFormats = new Set(selectedSavedFiles.value.map((file) => file.source_format));
    if (selectedFormats.size > 0 && !selectedFormats.has(nextSavedFile.source_format)) {
      errorMessage.value = "Välj filer med samma källformat.";
      return;
    }
    selectedSavedFileRefs.value = [...selectedSavedFileRefs.value, refValue];
    selectedSourceFormat.value = nextSavedFile.source_format;
    ensureOutputFormatForSource(nextSavedFile.source_format);
    errorMessage.value = null;
  }

  function removeSavedFile(index: number): void {
    const nextRefs = removeListItem(selectedSavedFileRefs.value, index);
    if (nextRefs) {
      selectedSavedFileRefs.value = nextRefs;
      errorMessage.value = null;
    }
  }

  function moveSavedFile(fromIndex: number, toIndex: number): void {
    const nextRefs = moveListItem(selectedSavedFileRefs.value, fromIndex, toIndex);
    if (nextRefs) {
      selectedSavedFileRefs.value = nextRefs;
      errorMessage.value = null;
    }
  }

  async function submitCurrentSelection(): Promise<void> {
    const request = buildCurrentRequest();
    if (!request) {
      return;
    }
    await submitRequest(request);
  }

  async function retryRequest(request: DocumentConverterSingleFileRequest): Promise<void> {
    restoreRequest(request);
    await submitRequest(request);
  }

  function restoreRequest(request: DocumentConverterSingleFileRequest): void {
    selectedSourceFormat.value = request.sourceFormat;
    selectedOutputFormat.value = request.outputFormat;
    if (request.kind === "upload") {
      sourceMode.value = "upload";
      selectedUploads.value = [...request.files];
      return;
    }
    sourceMode.value = "saved_file";
    selectedSavedFileRefs.value = request.savedFiles.map((file) => file.ref);
  }

  function buildCurrentRequest(): DocumentConverterSingleFileRequest | null {
    if (sourceMode.value === "upload") {
      if (selectedUploads.value.length === 0) {
        errorMessage.value = "Välj en fil som du vill konvertera.";
        return null;
      }
      if (selectedUploads.value.length > 10) {
        errorMessage.value = "Du kan konvertera högst 10 filer åt gången.";
        return null;
      }
      return {
        kind: "upload",
        files: [...selectedUploads.value],
        outputFormat: selectedOutputFormat.value,
        sourceFormat: selectedSourceFormat.value,
      };
    }
    if (selectedSavedFiles.value.length === 0) {
      errorMessage.value = "Välj en fil från Mina filer först.";
      return null;
    }
    if (selectedSavedFiles.value.length > 10) {
      errorMessage.value = "Du kan konvertera högst 10 filer åt gången.";
      return null;
    }
    const selectedFormats = new Set(selectedSavedFiles.value.map((file) => file.source_format));
    if (selectedFormats.size > 1 || !selectedFormats.has(selectedSourceFormat.value)) {
      errorMessage.value = "Välj filer med samma källformat.";
      return null;
    }
    return {
      kind: "saved_file",
      outputFormat: selectedOutputFormat.value,
      savedFiles: [...selectedSavedFiles.value],
      sourceFormat: selectedSourceFormat.value,
    };
  }

  async function submitRequest(request: DocumentConverterSingleFileRequest): Promise<void> {
    isSubmitting.value = true;
    errorMessage.value = null;
    try {
      const result = await submitDocumentConverterSingleFileRequest({
        request,
        setStatusMessage: (message) => {
          statusMessage.value = message;
        },
      });
      if (result.type === "pending") {
        statusMessage.value = result.statusMessage;
        return;
      }
      latestOutcome.value = result.outcome;
      statusMessage.value = result.statusMessage;
      if (result.outcome.type === "failed") {
        errorMessage.value = result.outcome.errorMessage;
      }
    } finally {
      isSubmitting.value = false;
    }
  }

  onMounted(() => {
    void loadSources();
  });

  return {
    availableOutputFormats,
    availableSourceFormats,
    errorMessage,
    isLoadingSources,
    isSubmitting,
    latestOutcome,
    loadSources,
    moveSavedFile,
    restoreRequest,
    retryRequest,
    savedFiles,
    moveLocalUpload,
    removeLocalUpload,
    removeSavedFile,
    selectLocalUploads,
    selectSavedFile,
    selectedOutputFormat,
    selectedSavedFileRefs,
    selectedSavedFiles,
    selectedSourceAccept,
    selectedSourceFormat,
    selectedSourceName,
    selectedUploads,
    setOutputFormat,
    setSourceFormat,
    setSourceMode,
    sourceMode,
    statusMessage,
    submitCurrentSelection,
  };
}
