<script setup lang="ts">
/**
 * Conversion Hub transcript host.
 *
 * Domain purpose:
 *   Compose the authenticated transcript lane's intake rail, workspace,
 *   speaker controls, and Gateway lifecycle runtime.
 *
 * Relationships:
 *   - Mounted directly by the `/apps/audio-transcription` route.
 *   - Keeps transcript state out of the Exam Converter components.
 */

import { computed, ref } from "vue";

import {
  buildSaveTranscriptRequest,
  registerTranscriptConversionHubJob,
  saveConversionHubTranscript,
} from "../../../api/conversionHubTranscriptSaves";
import TranscriptWorkflowRailShell from "./TranscriptWorkflowRailShell.vue";
import TranscriptWorkspaceShell from "./TranscriptWorkspaceShell.vue";
import { useTranscriptFormatterExports } from "./useTranscriptFormatterExports";
import { useTranscriptGatewayRuntime } from "./useTranscriptGatewayRuntime";
import { useTranscriptSourceFile, type TranscriptSpeakerMode } from "./useTranscriptSourceFile";
import { useTranscriptSpeakerOverlays } from "./useTranscriptSpeakerOverlays";

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

const conversionHubJobId = ref<string | null>(null);
const savedTranscriptId = ref<string | null>(null);
const saveStatus = ref<TranscriptSaveStatus>("idle");
const saveErrorMessage = ref<string | null>(null);
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
const {
  handleSpeakerOverlayChanged,
  loadSpeakerOverlays,
  resetSpeakerOverlayState,
  speakerOverlayCoverageComplete,
  speakerOverlayEntries,
  speakerOverlayErrorMessage,
  speakerOverlayStatus,
} = useTranscriptSpeakerOverlays({
  savedTranscriptId,
  transcript,
  resetFormatterExport: () => resetFormatterExportState(),
});
const {
  canRequestFormatterExport,
  formatterArtifactActionStates,
  formatterExportArtifacts,
  formatterExportErrorMessage,
  formatterExportStatus,
  handleDownloadFormatterArtifact,
  handleSaveFormatterArtifact,
  resetFormatterExportState,
} = useTranscriptFormatterExports({
  savedTranscriptId,
  canEditSpeakerOverlays,
  speakerOverlayCoverageComplete,
  speakerOverlayStatus,
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
