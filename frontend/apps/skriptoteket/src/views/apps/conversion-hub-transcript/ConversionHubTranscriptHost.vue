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

import { computed } from "vue";

import TranscriptWorkflowRailShell from "./TranscriptWorkflowRailShell.vue";
import TranscriptWorkspaceShell from "./TranscriptWorkspaceShell.vue";
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
  cancelTranscript,
  currentJob,
  errorMessage,
  resetRuntime,
  status: runtimeStatus,
  submitAndPoll,
  transcript,
} = useTranscriptGatewayRuntime();

const isRunning = computed(() => runtimeStatus.value === "running");
const canStartTranscript = computed(
  () => selectedTranscriptFile.value !== null && speakerError.value === null && !isRunning.value,
);

async function handleStartTranscript(): Promise<void> {
  const selection = selectedTranscriptFile.value;
  if (!selection || !canStartTranscript.value) return;
  try {
    await submitAndPoll({
      file: selection.file,
      speakerControl: speakerControl.value,
    });
  } catch {
    // Runtime state owns teacher-facing failure copy.
  }
}

function handleResetTranscriptChoices(): void {
  resetRuntime();
  resetTranscriptChoices();
}

function setSpeakerMode(mode: TranscriptSpeakerMode): void {
  speakerMode.value = mode;
}
</script>

<template>
  <TranscriptWorkflowRailShell
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
      :current-job="currentJob"
      :error-message="errorMessage"
      :runtime-status="runtimeStatus"
      :selected-transcript-file="selectedTranscriptFile"
      :transcript="transcript"
      :transcript-file-error="transcriptFileError"
      @files-dropped="selectDroppedTranscriptFiles"
      @transcript-file-selected="selectTranscriptFile"
    />
  </div>
</template>
