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

import type { components } from "../../../api/openapi";
import {
  getDocumentConverterJobStatus,
  listDocumentConverterSavedFiles,
  listDocumentConverterSingleFileRoutes,
  submitDocumentConverterSavedFileJob,
  submitDocumentConverterUploadJob,
  type DocumentConverterSavedFileSource,
  type DocumentConverterSingleFileRoute,
  type DocumentConverterSingleFileStatusResult,
} from "./documentConverterFileApi";

type ConversionHubJobStatus = components["schemas"]["ConversionHubJobStatus"];

export type DocumentConverterSingleFileSourceMode = "upload" | "saved_file";
export type DocumentConverterSingleFileOutput =
  | "pdf"
  | "docx"
  | "md";
export type DocumentConverterSingleFileSource =
  | "html"
  | "docx"
  | "md"
  | "pdf";

export type DocumentConverterSingleFileRequest =
    | {
        kind: "upload";
      files: File[];
      outputFormat: DocumentConverterSingleFileOutput;
      sourceFormat: DocumentConverterSingleFileSource;
    }
  | {
      kind: "saved_file";
      outputFormat: DocumentConverterSingleFileOutput;
      savedFile: DocumentConverterSavedFileSource;
      sourceFormat: DocumentConverterSingleFileSource;
    };

export type DocumentConverterSingleFileOutcome =
  | {
      type: "ready";
      entryId: string;
      filename: string;
      resultTypeLabel: string;
      sourceLabel: string;
      artifacts: DocumentConverterSingleFileArtifact[];
      request: DocumentConverterSingleFileRequest;
    }
  | {
      type: "failed";
      entryId: string;
      filename: string;
      resultTypeLabel: string;
      sourceLabel: string;
      errorMessage: string;
      request: DocumentConverterSingleFileRequest;
    };

export type DocumentConverterSingleFileArtifact = {
  filename: string;
  jobId: string;
  previewable: boolean;
};

const SOURCE_EXTENSIONS: Record<DocumentConverterSingleFileSource, string[]> = {
  html: [".html", ".htm"],
  docx: [".docx"],
  md: [".md", ".markdown"],
  pdf: [".pdf"],
};

const OUTPUT_LABELS: Record<DocumentConverterSingleFileOutput, string> = {
  docx: "DOCX",
  md: "Markdown",
  pdf: "PDF",
};

const TERMINAL_STATUSES = new Set<ConversionHubJobStatus>([
  "canceled",
  "failed",
  "succeeded",
]);

function isSingleFileSource(value: string): value is DocumentConverterSingleFileSource {
  return value === "html" || value === "docx" || value === "md" || value === "pdf";
}

function isSingleFileOutput(value: string): value is DocumentConverterSingleFileOutput {
  return value === "pdf" || value === "docx" || value === "md";
}

function sourceFormatFromFilename(filename: string): DocumentConverterSingleFileSource | null {
  const normalized = filename.toLowerCase();
  for (const [format, extensions] of Object.entries(SOURCE_EXTENSIONS)) {
    if (extensions.some((extension) => normalized.endsWith(extension))) {
      return format as DocumentConverterSingleFileSource;
    }
  }
  return null;
}

function sourceAcceptForFormats(formats: readonly DocumentConverterSingleFileSource[]): string {
  const extensions = formats.flatMap((format) => SOURCE_EXTENSIONS[format] ?? []);
  return Array.from(new Set(extensions)).join(",");
}

function outputFormatsForSource(
  routes: readonly DocumentConverterSingleFileRoute[],
  sourceFormat: DocumentConverterSingleFileSource,
): DocumentConverterSingleFileOutput[] {
  return routes
    .filter((route) => route.source_format === sourceFormat)
    .map((route) => route.output_format)
    .filter(isSingleFileOutput);
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

export function useDocumentConverterSingleFile() {
  const routes = ref<DocumentConverterSingleFileRoute[]>([]);
  const savedFiles = ref<DocumentConverterSavedFileSource[]>([]);
  const selectedSourceFormat = ref<DocumentConverterSingleFileSource>("html");
  const selectedOutputFormat = ref<DocumentConverterSingleFileOutput>("pdf");
  const sourceMode = ref<DocumentConverterSingleFileSourceMode>("upload");
  const selectedUploads = ref<File[]>([]);
  const selectedSavedFileRef = ref<string | null>(null);
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
  const selectedSavedFile = computed(() => {
    if (!selectedSavedFileRef.value) {
      return null;
    }
    return savedFiles.value.find((file) => file.ref === selectedSavedFileRef.value) ?? null;
  });
  const selectedSourceName = computed(() => {
    if (sourceMode.value === "upload") {
      if (selectedUploads.value.length === 0) {
        return "Ingen fil vald";
      }
      if (selectedUploads.value.length === 1) {
        return selectedUploads.value[0]?.name ?? "Ingen fil vald";
      }
      return `${selectedUploads.value.length.toLocaleString("sv-SE")} filer valda`;
    }
    return selectedSavedFile.value?.name ?? "Ingen fil vald";
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
      if (
        selectedSavedFileRef.value &&
        !savedFiles.value.some((file) => file.ref === selectedSavedFileRef.value)
      ) {
        selectedSavedFileRef.value = null;
      }
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
    if (index < 0 || index >= selectedUploads.value.length) {
      return;
    }
    selectedUploads.value = selectedUploads.value.filter((_file, fileIndex) => fileIndex !== index);
    errorMessage.value = null;
  }

  function moveLocalUpload(fromIndex: number, toIndex: number): void {
    if (
      fromIndex < 0 ||
      toIndex < 0 ||
      fromIndex >= selectedUploads.value.length ||
      toIndex >= selectedUploads.value.length
    ) {
      return;
    }
    const nextUploads = [...selectedUploads.value];
    const [file] = nextUploads.splice(fromIndex, 1);
    if (!file) {
      return;
    }
    nextUploads.splice(toIndex, 0, file);
    selectedUploads.value = nextUploads;
    errorMessage.value = null;
  }

  function selectSavedFile(refValue: string | null): void {
    selectedSavedFileRef.value = refValue;
    const nextSavedFile = savedFiles.value.find((file) => file.ref === refValue);
    if (nextSavedFile && isSingleFileSource(nextSavedFile.source_format)) {
      selectedSourceFormat.value = nextSavedFile.source_format;
      ensureOutputFormatForSource(nextSavedFile.source_format);
    }
    errorMessage.value = null;
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
    selectedSavedFileRef.value = request.savedFile.ref;
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
    if (!selectedSavedFile.value) {
      errorMessage.value = "Välj en fil från Mina filer först.";
      return null;
    }
    return {
      kind: "saved_file",
      outputFormat: selectedOutputFormat.value,
      savedFile: selectedSavedFile.value,
      sourceFormat: selectedSourceFormat.value,
    };
  }

  async function submitRequest(request: DocumentConverterSingleFileRequest): Promise<void> {
    isSubmitting.value = true;
    errorMessage.value = null;
    statusMessage.value = "Startar konverteringen...";
    try {
      const submitResult =
        request.kind === "upload"
          ? await submitDocumentConverterUploadJob({
              files: request.files,
              outputFormat: request.outputFormat,
              sourceFormat: request.sourceFormat,
            })
          : await submitDocumentConverterSavedFileJob({
              outputFormat: request.outputFormat,
              sourceFormat: request.sourceFormat,
              sourceRef: request.savedFile.ref,
            });
      const submittedJobs = submitResult.jobs;
      if (submittedJobs.length === 0) {
        throw new Error("Document Converter did not return a job.");
      }
      const sourceLabel = request.kind === "upload" ? "Lokal fil" : "Mina filer";
      const terminalResults = [];
      for (const submittedJob of submittedJobs) {
        terminalResults.push(
          await waitForTerminalJob({
            initialStatus: submittedJob.status,
            jobId: submittedJob.job_id,
            multiFile: submittedJobs.length > 1,
          }),
        );
      }
      if (terminalResults.some((result) => !TERMINAL_STATUSES.has(result.status))) {
        statusMessage.value =
          submittedJobs.length > 1 ? "Arbetar med filerna..." : "Arbetar med filen...";
        return;
      }

      const readyArtifacts = terminalResults.flatMap((result) => {
        if (result.status !== "succeeded" || !result.result_artifact) {
          return [];
        }
        return [
          {
            filename: result.result_artifact.filename ?? result.job_id,
            jobId: result.job_id,
            previewable: result.result_artifact.content_type === "application/pdf",
          },
        ];
      });
      if (readyArtifacts.length === terminalResults.length) {
        latestOutcome.value = {
          type: "ready",
          artifacts: readyArtifacts,
          entryId: `job:${terminalResults.map((result) => result.job_id).join(":")}`,
          filename:
            readyArtifacts.length === 1
              ? readyArtifacts[0]?.filename ?? submittedJobs[0]?.input_filename ?? "Resultat"
              : `${readyArtifacts.length.toLocaleString("sv-SE")} ${OUTPUT_LABELS[
                  request.outputFormat
                ]}-filer`,
          request,
          resultTypeLabel: OUTPUT_LABELS[request.outputFormat],
          sourceLabel,
        };
        statusMessage.value = null;
        return;
      }

      latestOutcome.value = {
        type: "failed",
        entryId: `job:${terminalResults.map((result) => result.job_id).join(":")}:failed`,
        errorMessage:
          terminalResults.find((result) => result.error)?.error ??
          submittedJobs.find((job) => job.error)?.error ??
          "Konverteringen kunde inte slutföras.",
        filename: submittedJobs[0]?.input_filename ?? "Resultat",
        request,
        resultTypeLabel: OUTPUT_LABELS[request.outputFormat],
        sourceLabel,
      };
      errorMessage.value = latestOutcome.value.errorMessage;
      statusMessage.value = null;
    } catch {
      latestOutcome.value = {
        type: "failed",
        entryId: `job:failed:${Date.now()}`,
        errorMessage: "Konverteringen kunde inte starta.",
        filename:
          request.kind === "upload" ? request.files[0]?.name ?? "Resultat" : request.savedFile.name,
        request,
        resultTypeLabel: OUTPUT_LABELS[request.outputFormat],
        sourceLabel: request.kind === "upload" ? "Lokal fil" : "Mina filer",
      };
      errorMessage.value = latestOutcome.value.errorMessage;
      statusMessage.value = null;
    } finally {
      isSubmitting.value = false;
    }
  }

  async function waitForTerminalJob(params: {
    initialStatus: ConversionHubJobStatus;
    jobId: string;
    multiFile: boolean;
  }): Promise<DocumentConverterSingleFileStatusResult> {
    if (TERMINAL_STATUSES.has(params.initialStatus)) {
      return await getDocumentConverterJobStatus({ jobId: params.jobId });
    }

    let attempts = 0;
    let currentStatus = params.initialStatus;
    let currentResult: DocumentConverterSingleFileStatusResult = {
      error: null,
      job_id: params.jobId,
      result_artifact: null,
      status: currentStatus,
    };

    while (!TERMINAL_STATUSES.has(currentStatus) && attempts < 20) {
      statusMessage.value = params.multiFile ? "Arbetar med filerna..." : "Arbetar med filen...";
      await sleep(1000);
      currentResult = await getDocumentConverterJobStatus({ jobId: params.jobId });
      currentStatus = currentResult.status;
      attempts += 1;
    }

    if (currentResult.job_id !== params.jobId || currentResult.status !== currentStatus) {
      currentResult = await getDocumentConverterJobStatus({ jobId: params.jobId });
    }
    return currentResult;
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
    restoreRequest,
    retryRequest,
    savedFiles,
    moveLocalUpload,
    removeLocalUpload,
    selectLocalUploads,
    selectSavedFile,
    selectedOutputFormat,
    selectedSavedFile,
    selectedSavedFileRef,
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
