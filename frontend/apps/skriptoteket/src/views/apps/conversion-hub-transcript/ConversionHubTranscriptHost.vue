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

import { computed, ref } from "vue";

import {
  downloadConversionHubTranscriptFormatterArtifact,
  saveConversionHubTranscriptFormatterArtifact,
  type TranscriptFormatterArtifactKey,
} from "../../../api/conversionHubTranscriptFormatterArtifactActions";
import {
  requestConversionHubTranscriptFormatterReplay,
  type ConversionHubTranscriptFormatterArtifactRef,
} from "../../../api/conversionHubTranscriptFormatterReplay";
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
} = useTranscriptGatewayRuntime();

type TranscriptSaveStatus = "idle" | "saving" | "saved" | "failed";
type SpeakerOverlayStatus = "idle" | "loading" | "saving" | "saved" | "failed";
type FormatterReplayStatus = "idle" | "running" | "succeeded" | "failed";

const conversionHubJobId = ref<string | null>(null);
const savedTranscriptId = ref<string | null>(null);
const saveStatus = ref<TranscriptSaveStatus>("idle");
const saveErrorMessage = ref<string | null>(null);
const speakerOverlayEntries = ref<ConversionHubTranscriptSpeakerOverlayEntry[]>([]);
const speakerOverlayStatus = ref<SpeakerOverlayStatus>("idle");
const speakerOverlayErrorMessage = ref<string | null>(null);
const formatterReplayArtifacts = ref<ConversionHubTranscriptFormatterArtifactRef[]>([]);
const formatterReplayStatus = ref<FormatterReplayStatus>("idle");
const formatterReplayErrorMessage = ref<string | null>(null);
const formatterArtifactActionStates = ref<FormatterArtifactActionStates>({});
const isRunning = computed(() => runtimeStatus.value === "running");
const canStartTranscript = computed(
  () => selectedTranscriptFile.value !== null && speakerError.value === null && !isRunning.value,
);
const canSaveTranscript = computed(
  () =>
    runtimeStatus.value === "succeeded" &&
    transcript.value !== null &&
    conversionHubJobId.value !== null &&
    saveStatus.value !== "saving" &&
    saveStatus.value !== "saved",
);
const canEditSpeakerOverlays = computed(
  () => saveStatus.value === "saved" && savedTranscriptId.value !== null,
);
const canRequestFormatterReplay = computed(
  () =>
    saveStatus.value === "saved" &&
    savedTranscriptId.value !== null &&
    speakerOverlayEntries.value.length > 0 &&
    speakerOverlayStatus.value === "saved" &&
    formatterReplayStatus.value !== "running",
);

function resetFormatterReplayState(): void {
  formatterReplayArtifacts.value = [];
  formatterReplayStatus.value = "idle";
  formatterReplayErrorMessage.value = null;
  formatterArtifactActionStates.value = {};
}

function resetSpeakerOverlayState(): void {
  savedTranscriptId.value = null;
  speakerOverlayEntries.value = [];
  speakerOverlayStatus.value = "idle";
  speakerOverlayErrorMessage.value = null;
  resetFormatterReplayState();
}

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
    const registered = await registerTranscriptConversionHubJob({
      request: {
        upstream_job_id: lastJobId.value,
        input_filename: selection.name,
        correlation_id: lastCorrelationId.value,
        status: "succeeded",
      },
    });
    conversionHubJobId.value = registered.job_id;
  } catch {
    if (runtimeStatus.value === "succeeded") {
      saveStatus.value = "failed";
      saveErrorMessage.value = "Transkriptet är klart men kunde inte förberedas för sparning.";
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
  const selection = selectedTranscriptFile.value;
  const transcriptJson = transcript.value;
  const localJobId = conversionHubJobId.value;
  const sirJobId = lastJobId.value;
  if (!selection || !transcriptJson || !localJobId || !sirJobId) return;
  saveStatus.value = "saving";
  saveErrorMessage.value = null;
  try {
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
    saveStatus.value = "saved";
    await loadSpeakerOverlays(saved.transcript_id);
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
    speakerOverlayStatus.value = response.overlays.length > 0 ? "saved" : "idle";
  } catch {
    speakerOverlayStatus.value = "failed";
    speakerOverlayErrorMessage.value = "Talarnamn kunde inte hämtas.";
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
  if (speakerOverlayStatus.value === "saved") {
    speakerOverlayStatus.value = "idle";
  }
  speakerOverlayErrorMessage.value = null;
  resetFormatterReplayState();
}

async function handleSaveSpeakerOverlays(): Promise<void> {
  const transcriptId = savedTranscriptId.value;
  if (!transcriptId) return;
  speakerOverlayStatus.value = "saving";
  speakerOverlayErrorMessage.value = null;
  try {
    const response = await updateConversionHubTranscriptSpeakerOverlays({
      transcriptId,
      request: {
        overlays: speakerOverlayEntries.value
          .map((entry) => ({
            canonical_speaker_label: entry.canonical_speaker_label,
            display_name: entry.display_name.trim(),
          }))
          .filter((entry) => entry.display_name.length > 0),
      },
    });
    speakerOverlayEntries.value = response.overlays;
    speakerOverlayStatus.value = "saved";
    resetFormatterReplayState();
  } catch {
    speakerOverlayStatus.value = "failed";
    speakerOverlayErrorMessage.value = "Talarnamnen kunde inte sparas.";
  }
}

async function handleRequestFormatterReplay(): Promise<void> {
  const transcriptId = savedTranscriptId.value;
  if (!transcriptId || !canRequestFormatterReplay.value) return;
  formatterReplayStatus.value = "running";
  formatterReplayErrorMessage.value = null;
  formatterReplayArtifacts.value = [];
  try {
    const replay = await requestConversionHubTranscriptFormatterReplay({ transcriptId });
    formatterReplayArtifacts.value = replay.artifacts;
    formatterArtifactActionStates.value = {};
    formatterReplayStatus.value = "succeeded";
  } catch {
    formatterReplayStatus.value = "failed";
    formatterReplayErrorMessage.value = "Exportfiler kunde inte skapas. Försök igen.";
  }
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
  artifact: ConversionHubTranscriptFormatterArtifactRef,
): Promise<void> {
  const transcriptId = savedTranscriptId.value;
  if (!transcriptId) {
    setFormatterArtifactActionState(artifact.artifact_key, { download: "failed" });
    return;
  }
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
  artifact: ConversionHubTranscriptFormatterArtifactRef,
): Promise<void> {
  const transcriptId = savedTranscriptId.value;
  if (!transcriptId) {
    setFormatterArtifactActionState(artifact.artifact_key, { save: "failed" });
    return;
  }
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
  <div class="min-w-0">
    <TranscriptWorkspaceShell
      :abort-state="abortState"
      :current-job="currentJob"
      :can-request-formatter-replay="canRequestFormatterReplay"
      :can-save-transcript="canSaveTranscript"
      :error-message="errorMessage"
      :formatter-artifact-action-states="formatterArtifactActionStates"
      :formatter-replay-artifacts="formatterReplayArtifacts"
      :formatter-replay-error-message="formatterReplayErrorMessage"
      :formatter-replay-status="formatterReplayStatus"
      :runtime-status="runtimeStatus"
      :selected-transcript-file="selectedTranscriptFile"
      :save-error-message="saveErrorMessage"
      :save-status="saveStatus"
      :transcript="transcript"
      :transcript-file-error="transcriptFileError"
      :can-edit-speaker-overlays="canEditSpeakerOverlays"
      :speaker-overlay-entries="speakerOverlayEntries"
      :speaker-overlay-error-message="speakerOverlayErrorMessage"
      :speaker-overlay-status="speakerOverlayStatus"
      @download-formatter-artifact="handleDownloadFormatterArtifact"
      @files-dropped="selectDroppedTranscriptFiles"
      @request-formatter-replay="handleRequestFormatterReplay"
      @save-formatter-artifact="handleSaveFormatterArtifact"
      @save-transcript="handleSaveTranscript"
      @save-speaker-overlays="handleSaveSpeakerOverlays"
      @speaker-overlay-changed="handleSpeakerOverlayChanged"
      @transcript-file-selected="selectTranscriptFile"
    />
  </div>
</template>
