<script setup lang="ts">
/**
 * Conversion Hub transcript host.
 *
 * Domain purpose:
 *   Compose the authenticated transcript lane's intake rail, workspace,
 *   speaker controls, and Gateway lifecycle runtime.
 *
 * Relationships:
 *   - Rendered by `ExamConverterAuthenticatedView` when transcript mode is
 *     selected.
 *   - Keeps transcript state out of the existing Exam Converter components.
 */

import { computed, onBeforeUnmount, ref } from "vue";

import {
  downloadConversionHubTranscriptFormatterArtifact,
  saveConversionHubTranscriptFormatterArtifact,
  type TranscriptFormatterArtifactKey,
} from "../../../api/conversionHubTranscriptFormatterArtifactActions";
import {
  type ConversionHubTranscriptFormatterArtifactRef,
  type ConversionHubTranscriptFormatterExportResponse,
  type ConversionHubTranscriptFormatterExportStatus,
  getConversionHubTranscriptFormatterExport,
  requestConversionHubTranscriptFormatterExport,
} from "../../../api/conversionHubTranscriptFormatterExports";
import {
  buildSaveTranscriptRequest,
  getConversionHubTranscriptSpeakerOverlays,
  registerTranscriptConversionHubJob,
  saveConversionHubTranscript,
  updateConversionHubTranscriptSpeakerOverlays,
  type ConversionHubTranscriptSpeakerOverlayEntry,
} from "../../../api/conversionHubTranscriptSaves";
import { triggerBrowserDownload } from "../exam-converter/browserDownload";
import TranscriptWorkflowRailShell from "./TranscriptWorkflowRailShell.vue";
import TranscriptWorkspaceShell from "./TranscriptWorkspaceShell.vue";
import {
  formatterArtifactActionState,
  type FormatterArtifactActionState,
  type FormatterArtifactActionStates,
} from "./transcriptFormatterArtifactActions";
import { useTranscriptGatewayRuntime } from "./useTranscriptGatewayRuntime";
import { useTranscriptSourceFile, type TranscriptSpeakerMode } from "./useTranscriptSourceFile";

const {
  clearTranscriptFile,
  maxSpeakers,
  minSpeakers,
  resetTranscriptChoices,
  selectDroppedTranscriptFiles,
  selectTranscriptFile,
  selectedTranscriptFile,
  speakerControl,
  speakerCount,
  speakerError,
  speakerMode,
  transcriptFileError,
} = useTranscriptSourceFile();

const {
  abortState,
  cancelTranscript,
  currentJob,
  errorMessage,
  resetRuntime,
  status: runtimeStatus,
  submitAndPoll,
  transcript,
  lastCorrelationId,
  lastJobId,
  uploadState,
} = useTranscriptGatewayRuntime();

type TranscriptSaveStatus = "idle" | "saving" | "saved" | "failed";
type SpeakerOverlayStatus = "idle" | "loading" | "saving" | "saved" | "failed";
type FormatterExportStatus = ConversionHubTranscriptFormatterExportStatus;
type TranscriptFormatterRequestedArtifact =
  ConversionHubTranscriptFormatterArtifactRef["requested_artifact"];
const SPEAKER_OVERLAY_AUTOSAVE_DELAY_MS = 500;

const conversionHubJobId = ref<string | null>(null);
const savedTranscriptId = ref<string | null>(null);
const saveStatus = ref<TranscriptSaveStatus>("idle");
const saveErrorMessage = ref<string | null>(null);
const speakerOverlayEntries = ref<ConversionHubTranscriptSpeakerOverlayEntry[]>([]);
const speakerOverlayStatus = ref<SpeakerOverlayStatus>("idle");
const speakerOverlayErrorMessage = ref<string | null>(null);
const formatterExportArtifacts = ref<ConversionHubTranscriptFormatterArtifactRef[]>([]);
const formatterExportStatus = ref<FormatterExportStatus>("not_requested");
const formatterExportErrorMessage = ref<string | null>(null);
const formatterExportRequestInFlight = ref(false);
const formatterArtifactActionStates = ref<FormatterArtifactActionStates>({});
const speakerOverlayRevision = ref(0);
let speakerOverlayAutosaveTimer: ReturnType<typeof window.setTimeout> | null = null;
let speakerOverlayGeneration = 0;
let speakerOverlaySaveInFlight = false;
let speakerOverlaySaveQueued = false;
const isRunning = computed(() => runtimeStatus.value === "running");
const canStartTranscript = computed(
  () => selectedTranscriptFile.value !== null && speakerError.value === null && !isRunning.value,
);
const canSaveTranscript = computed(
  () =>
    runtimeStatus.value === "succeeded" &&
    transcript.value !== null &&
    selectedTranscriptFile.value !== null &&
    lastJobId.value !== null &&
    saveStatus.value === "failed",
);
const canEditSpeakerOverlays = computed(
  () => saveStatus.value === "saved" && savedTranscriptId.value !== null,
);
const canRequestFormatterExport = computed(
  () =>
    saveStatus.value === "saved" &&
    savedTranscriptId.value !== null &&
    speakerOverlayCoverageComplete.value &&
    speakerOverlayStatus.value === "saved" &&
    !formatterExportRequestInFlight.value,
);
const speakerOverlayCoverageComplete = computed(() =>
  speakerOverlayEntriesCoverTranscript(speakerOverlayEntries.value),
);

function resetFormatterExportState(): void {
  formatterExportArtifacts.value = [];
  formatterExportStatus.value = "not_requested";
  formatterExportErrorMessage.value = null;
  formatterExportRequestInFlight.value = false;
  formatterArtifactActionStates.value = {};
}

function clearSpeakerOverlayAutosave(): void {
  if (speakerOverlayAutosaveTimer === null) return;
  window.clearTimeout(speakerOverlayAutosaveTimer);
  speakerOverlayAutosaveTimer = null;
}

function resetSpeakerOverlayState(): void {
  clearSpeakerOverlayAutosave();
  speakerOverlayGeneration += 1;
  speakerOverlaySaveInFlight = false;
  speakerOverlaySaveQueued = false;
  speakerOverlayRevision.value = 0;
  savedTranscriptId.value = null;
  speakerOverlayEntries.value = [];
  speakerOverlayStatus.value = "idle";
  speakerOverlayErrorMessage.value = null;
  resetFormatterExportState();
}

onBeforeUnmount(() => {
  clearSpeakerOverlayAutosave();
  speakerOverlayGeneration += 1;
});

async function handleStartTranscript(): Promise<void> {
  const selection = selectedTranscriptFile.value;
  if (!selection || !canStartTranscript.value) return;
  conversionHubJobId.value = null;
  saveStatus.value = "idle";
  saveErrorMessage.value = null;
  resetSpeakerOverlayState();
  try {
    const transcriptJson = await submitAndPoll({
      file: selection.file,
      speakerControl: speakerControl.value,
    });
    if (!transcriptJson || !lastJobId.value) return;
    await persistTranscript();
  } catch {
    if (runtimeStatus.value === "succeeded") {
      saveStatus.value = "failed";
      saveErrorMessage.value = "Transkriptet kunde inte sparas. Försök igen.";
    }
  }
}

function handleResetTranscriptChoices(): void {
  resetRuntime();
  resetTranscriptChoices();
  conversionHubJobId.value = null;
  saveStatus.value = "idle";
  saveErrorMessage.value = null;
  resetSpeakerOverlayState();
}

function setSpeakerMode(mode: TranscriptSpeakerMode): void {
  speakerMode.value = mode;
}

async function handleSaveTranscript(): Promise<void> {
  await persistTranscript();
}

async function ensureRegisteredTranscriptJob(selectionName: string): Promise<string | null> {
  if (conversionHubJobId.value) return conversionHubJobId.value;
  const sirJobId = lastJobId.value;
  if (!sirJobId) return null;
  const registered = await registerTranscriptConversionHubJob({
    request: {
      upstream_job_id: sirJobId,
      input_filename: selectionName,
      correlation_id: lastCorrelationId.value,
      status: "succeeded",
    },
  });
  conversionHubJobId.value = registered.job_id;
  return registered.job_id;
}

async function persistTranscript(): Promise<void> {
  const selection = selectedTranscriptFile.value;
  const transcriptJson = transcript.value;
  const sirJobId = lastJobId.value;
  if (!selection || !transcriptJson || !sirJobId) return;
  saveStatus.value = "saving";
  saveErrorMessage.value = null;
  try {
    const localJobId = await ensureRegisteredTranscriptJob(selection.name);
    if (!localJobId) throw new Error("Missing transcript job registration");
    const saved = await saveConversionHubTranscript({
      conversionHubJobId: localJobId,
      request: buildSaveTranscriptRequest({
        correlationId: lastCorrelationId.value,
        sirConvertJobId: sirJobId,
        sourceFilename: selection.name,
        speakerControl: speakerControl.value,
        transcript: transcriptJson,
      }),
    });
    savedTranscriptId.value = saved.transcript_id;
    await loadSpeakerOverlays(saved.transcript_id);
    saveStatus.value = "saved";
  } catch {
    saveStatus.value = "failed";
    saveErrorMessage.value = "Transkriptet kunde inte sparas. Försök igen.";
  }
}

async function loadSpeakerOverlays(transcriptId: string): Promise<void> {
  speakerOverlayStatus.value = "loading";
  speakerOverlayErrorMessage.value = null;
  try {
    const response = await getConversionHubTranscriptSpeakerOverlays({ transcriptId });
    speakerOverlayEntries.value = response.overlays;
    speakerOverlayRevision.value = 0;
    speakerOverlayStatus.value = speakerOverlayEntriesCoverTranscript(response.overlays)
      ? "saved"
      : "idle";
  } catch {
    speakerOverlayStatus.value = "failed";
    speakerOverlayErrorMessage.value = "Namnen kunde inte hämtas.";
  }
}

function handleSpeakerOverlayChanged(label: string, displayName: string): void {
  const nextEntries = speakerOverlayEntries.value.filter(
    (entry) => entry.canonical_speaker_label !== label,
  );
  if (displayName.length > 0) {
    nextEntries.push({ canonical_speaker_label: label, display_name: displayName });
  }
  speakerOverlayEntries.value = nextEntries;
  speakerOverlayRevision.value += 1;
  speakerOverlayStatus.value = "idle";
  speakerOverlayErrorMessage.value = null;
  resetFormatterExportState();
  scheduleSpeakerOverlayAutosave();
}

function scheduleSpeakerOverlayAutosave(): void {
  const transcriptId = savedTranscriptId.value;
  if (!transcriptId) return;
  clearSpeakerOverlayAutosave();
  speakerOverlayAutosaveTimer = window.setTimeout(() => {
    speakerOverlayAutosaveTimer = null;
    void persistSpeakerOverlays();
  }, SPEAKER_OVERLAY_AUTOSAVE_DELAY_MS);
}

async function persistSpeakerOverlays(): Promise<void> {
  const transcriptId = savedTranscriptId.value;
  if (!transcriptId) return;
  if (speakerOverlaySaveInFlight) {
    speakerOverlaySaveQueued = true;
    return;
  }
  const generationAtStart = speakerOverlayGeneration;
  const revisionAtStart = speakerOverlayRevision.value;
  const overlays = speakerOverlayEntries.value
    .map((entry) => ({
      canonical_speaker_label: entry.canonical_speaker_label,
      display_name: entry.display_name.trim(),
    }))
    .filter((entry) => entry.display_name.length > 0);
  speakerOverlaySaveInFlight = true;
  speakerOverlayStatus.value = "saving";
  speakerOverlayErrorMessage.value = null;
  try {
    const response = await updateConversionHubTranscriptSpeakerOverlays({
      transcriptId,
      request: { overlays },
    });
    if (
      generationAtStart === speakerOverlayGeneration &&
      revisionAtStart === speakerOverlayRevision.value
    ) {
      speakerOverlayEntries.value = response.overlays;
      speakerOverlayStatus.value = speakerOverlayEntriesCoverTranscript(response.overlays)
        ? "saved"
        : "idle";
    }
  } catch {
    if (
      generationAtStart === speakerOverlayGeneration &&
      revisionAtStart === speakerOverlayRevision.value
    ) {
      speakerOverlayStatus.value = "failed";
      speakerOverlayErrorMessage.value = "Namnen kunde inte sparas.";
    }
  } finally {
    const changedDuringSave = revisionAtStart !== speakerOverlayRevision.value;
    speakerOverlaySaveInFlight = false;
    if (
      generationAtStart === speakerOverlayGeneration &&
      (speakerOverlaySaveQueued || changedDuringSave)
    ) {
      speakerOverlaySaveQueued = false;
      scheduleSpeakerOverlayAutosave();
    }
  }
}

function speakerOverlayEntriesCoverTranscript(
  entries: readonly ConversionHubTranscriptSpeakerOverlayEntry[],
): boolean {
  const speakerLabels = new Set(transcript.value?.segments.map((segment) => segment.speakerLabel));
  if (speakerLabels.size === 0) return false;
  const namedLabels = new Set(
    entries
      .filter((entry) => entry.display_name.trim().length > 0)
      .map((entry) => entry.canonical_speaker_label),
  );
  return [...speakerLabels].every((label) => namedLabels.has(label));
}

function applyFormatterExportState(
  response: ConversionHubTranscriptFormatterExportResponse,
): void {
  formatterExportStatus.value = response.status;
  formatterExportArtifacts.value = response.status === "succeeded" ? response.artifacts : [];
  formatterArtifactActionStates.value = {};
  formatterExportErrorMessage.value =
    response.status === "failed"
      ? response.error_message ?? "Filerna kunde inte skapas. Försök igen."
      : null;
}

async function requestOrRefreshFormatterExport():
  Promise<ConversionHubTranscriptFormatterExportResponse | null> {
  const transcriptId = savedTranscriptId.value;
  if (!transcriptId || !canRequestFormatterExport.value) return null;
  const shouldRefresh =
    formatterExportStatus.value === "pending" || formatterExportStatus.value === "running";
  if (!shouldRefresh) {
    formatterExportStatus.value = "running";
    formatterExportArtifacts.value = [];
  }
  formatterExportRequestInFlight.value = true;
  formatterExportErrorMessage.value = null;
  try {
    const exportState = shouldRefresh
      ? await getConversionHubTranscriptFormatterExport({ transcriptId })
      : await requestConversionHubTranscriptFormatterExport({ transcriptId });
    applyFormatterExportState(exportState);
    return exportState;
  } catch {
    formatterExportStatus.value = "failed";
    formatterExportErrorMessage.value = "Filerna kunde inte skapas. Försök igen.";
    return null;
  } finally {
    formatterExportRequestInFlight.value = false;
  }
}

function artifactForRequestedArtifact(
  requestedArtifact: TranscriptFormatterRequestedArtifact,
): ConversionHubTranscriptFormatterArtifactRef | null {
  return (
    formatterExportArtifacts.value.find(
      (artifact) => artifact.requested_artifact === requestedArtifact,
    ) ?? null
  );
}

async function ensureFormatterArtifact(
  requestedArtifact: TranscriptFormatterRequestedArtifact,
): Promise<ConversionHubTranscriptFormatterArtifactRef | null> {
  const existingArtifact = artifactForRequestedArtifact(requestedArtifact);
  if (existingArtifact) return existingArtifact;
  const exportState = await requestOrRefreshFormatterExport();
  const createdArtifact =
    exportState?.artifacts.find(
      (artifact) => artifact.requested_artifact === requestedArtifact,
    ) ?? null;
  if (createdArtifact) return createdArtifact;
  if (exportState?.status === "pending" || exportState?.status === "running") return null;
  formatterExportStatus.value = "failed";
  formatterExportErrorMessage.value = "Filerna kunde inte skapas. Försök igen.";
  return null;
}

function setFormatterArtifactActionState(
  artifactKey: TranscriptFormatterArtifactKey,
  patch: Partial<FormatterArtifactActionState>,
): void {
  const current = formatterArtifactActionState(
    formatterArtifactActionStates.value,
    artifactKey,
  );
  formatterArtifactActionStates.value = {
    ...formatterArtifactActionStates.value,
    [artifactKey]: {
      ...current,
      ...patch,
    },
  };
}

async function handleDownloadFormatterArtifact(
  requestedArtifact: TranscriptFormatterRequestedArtifact,
): Promise<void> {
  const transcriptId = savedTranscriptId.value;
  if (!transcriptId) return;
  const artifact = await ensureFormatterArtifact(requestedArtifact);
  if (!artifact) return;
  setFormatterArtifactActionState(artifact.artifact_key, {
    download: "running",
    save: formatterArtifactActionState(
      formatterArtifactActionStates.value,
      artifact.artifact_key,
    ).save,
  });
  try {
    const response = await downloadConversionHubTranscriptFormatterArtifact({
      artifactKey: artifact.artifact_key,
      transcriptId,
    });
    triggerBrowserDownload(response.blob, response.filename ?? artifact.filename);
    setFormatterArtifactActionState(artifact.artifact_key, { download: "succeeded" });
  } catch {
    setFormatterArtifactActionState(artifact.artifact_key, { download: "failed" });
  }
}

async function handleSaveFormatterArtifact(
  requestedArtifact: TranscriptFormatterRequestedArtifact,
): Promise<void> {
  const transcriptId = savedTranscriptId.value;
  if (!transcriptId) return;
  const artifact = await ensureFormatterArtifact(requestedArtifact);
  if (!artifact) return;
  setFormatterArtifactActionState(artifact.artifact_key, {
    save: "running",
    savedFilename: null,
  });
  try {
    const saved = await saveConversionHubTranscriptFormatterArtifact({
      artifactKey: artifact.artifact_key,
      transcriptId,
    });
    setFormatterArtifactActionState(artifact.artifact_key, {
      save: "succeeded",
      savedFilename: saved.vault_artifact.name,
    });
  } catch {
    setFormatterArtifactActionState(artifact.artifact_key, { save: "failed" });
  }
}
</script>

<template>
  <div
    class="col-span-full grid min-h-0 min-w-0 grid-cols-1 items-stretch min-[821px]:grid-cols-[minmax(14rem,17rem)_minmax(0,1fr)] min-[1181px]:grid-cols-[minmax(15rem,18rem)_minmax(0,1fr)]"
    data-test="transcript-host-layout"
  >
    <TranscriptWorkflowRailShell
      :abort-state="abortState"
      :can-start-transcript="canStartTranscript"
      :is-running="isRunning"
      :max-speakers="maxSpeakers"
      :min-speakers="minSpeakers"
      :selected-transcript-file="selectedTranscriptFile"
      :speaker-count="speakerCount"
      :speaker-error="speakerError"
      :speaker-mode="speakerMode"
      :transcript-file-error="transcriptFileError"
      @cancel-transcript="cancelTranscript"
      @clear-transcript-file="clearTranscriptFile"
      @max-speakers-changed="maxSpeakers = $event"
      @min-speakers-changed="minSpeakers = $event"
      @reset-transcript-choices="handleResetTranscriptChoices"
      @speaker-count-changed="speakerCount = $event"
      @speaker-mode-changed="setSpeakerMode"
      @start-transcript="handleStartTranscript"
      @transcript-file-selected="selectTranscriptFile"
    />
    <div class="min-h-0 min-w-0">
      <TranscriptWorkspaceShell
        :abort-state="abortState"
        :current-job="currentJob"
        :can-request-formatter-export="canRequestFormatterExport"
        :can-save-transcript="canSaveTranscript"
        :error-message="errorMessage"
        :formatter-artifact-action-states="formatterArtifactActionStates"
        :formatter-export-artifacts="formatterExportArtifacts"
        :formatter-export-error-message="formatterExportErrorMessage"
        :formatter-export-status="formatterExportStatus"
        :runtime-status="runtimeStatus"
        :selected-transcript-file="selectedTranscriptFile"
        :save-error-message="saveErrorMessage"
        :save-status="saveStatus"
        :transcript="transcript"
        :transcript-file-error="transcriptFileError"
        :upload-state="uploadState"
        :can-edit-speaker-overlays="canEditSpeakerOverlays"
        :speaker-overlay-entries="speakerOverlayEntries"
        :speaker-overlay-error-message="speakerOverlayErrorMessage"
        :speaker-overlay-status="speakerOverlayStatus"
        @download-formatter-artifact="handleDownloadFormatterArtifact"
        @files-dropped="selectDroppedTranscriptFiles"
        @save-formatter-artifact="handleSaveFormatterArtifact"
        @save-transcript="handleSaveTranscript"
        @speaker-overlay-changed="handleSpeakerOverlayChanged"
        @transcript-file-selected="selectTranscriptFile"
      />
    </div>
  </div>
</template>
