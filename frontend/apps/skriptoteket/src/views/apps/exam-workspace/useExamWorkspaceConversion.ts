/**
 * Exam workspace DOCX import and conversion lifecycle.
 * Owns polling, retry backoff and disposal; the document owner applies the
 * completed response through its callback.
 */

import { computed, onScopeDispose, ref } from "vue";

import {
  getExamWorkspaceConversionStatus,
  getExamWorkspaceDocument,
  importExamWorkspaceDocument as requestImportExamWorkspaceDocument,
} from "../../../api/examWorkspace";
import type {
  ExamWorkspaceConversionStatus,
  ExamWorkspaceDocumentResponse,
} from "../../../api/examWorkspace";
import { useToast } from "../../../composables/useToast";

export const EXAM_WORKSPACE_CONVERSION_POLL_MS = 3000;
const CONVERSION_MAX_POLL_MS = 30_000;
const STATUS_FAILURE_COPY = "Det gick inte att hämta konverteringen eller öppna provet. Försöker igen …";
const IMPORT_FAILURE_COPY = "Det gick inte att läsa in provet. Försök igen.";

export function useExamWorkspaceConversion(
  isBusy: () => boolean,
  onCompleted: (response: ExamWorkspaceDocumentResponse) => void,
) {
  const toast = useToast();
  const isImporting = ref(false);
  const conversionStatus = ref<ExamWorkspaceConversionStatus | null>(null);
  const isConverting = ref(false);
  const conversionError = ref<string | null>(null);
  let pollTimer: ReturnType<typeof setTimeout> | null = null;
  let generation = 0;
  let pollFailures = 0;
  let statusRequestPending = false;

  const conversionMessage = computed(() => {
    if (isConverting.value) return "Konverterar provet …";
    if (conversionStatus.value?.state === "failed") {
      return conversionStatus.value.error_message ?? IMPORT_FAILURE_COPY;
    }
    return conversionError.value;
  });

  function stopPolling(): void {
    if (pollTimer !== null) {
      clearTimeout(pollTimer);
      pollTimer = null;
    }
  }

  function schedulePoll(pollGeneration: number): void {
    stopPolling();
    const delay = Math.min(
      EXAM_WORKSPACE_CONVERSION_POLL_MS * 2 ** Math.max(0, pollFailures - 1),
      CONVERSION_MAX_POLL_MS,
    );
    pollTimer = setTimeout(() => {
      pollTimer = null;
      void refreshConversion(pollGeneration);
    }, delay);
  }

  async function applyConversionStatus(
    status: ExamWorkspaceConversionStatus,
    pollGeneration: number,
  ): Promise<void> {
    if (pollGeneration !== generation) return;
    conversionStatus.value = status;
    if (status.state === "failed") {
      isConverting.value = false;
      conversionError.value = null;
      stopPolling();
    } else if (status.state === "succeeded") {
      const response = await getExamWorkspaceDocument(status.lineage_id);
      if (pollGeneration !== generation) return;
      onCompleted(response);
      isConverting.value = false;
      conversionError.value = null;
      stopPolling();
    } else {
      pollFailures = 0;
      schedulePoll(pollGeneration);
    }
  }

  async function refreshConversion(pollGeneration: number): Promise<void> {
    const status = conversionStatus.value;
    if (!status || statusRequestPending || !isConverting.value) return;
    statusRequestPending = true;
    try {
      const next = status.state === "succeeded" || status.state === "failed"
        ? status
        : await getExamWorkspaceConversionStatus(status.job_id);
      await applyConversionStatus(next, pollGeneration);
      if (pollGeneration === generation) {
        pollFailures = 0;
        conversionError.value = null;
      }
    } catch {
      if (pollGeneration !== generation) return;
      conversionError.value = STATUS_FAILURE_COPY;
      pollFailures += 1;
      schedulePoll(pollGeneration);
    } finally {
      statusRequestPending = false;
    }
  }

  function retryConversionStatus(): void {
    stopPolling();
    void refreshConversion(generation);
  }

  async function importDocument(file: File): Promise<void> {
    if (isBusy()) return;
    const pollGeneration = ++generation;
    isImporting.value = true;
    conversionError.value = null;
    conversionStatus.value = null;
    pollFailures = 0;
    try {
      const status = await requestImportExamWorkspaceDocument(file);
      if (pollGeneration !== generation) return;
      isConverting.value = true;
      conversionStatus.value = status;
      await refreshConversion(pollGeneration);
    } catch {
      if (pollGeneration !== generation) return;
      conversionError.value = IMPORT_FAILURE_COPY;
      toast.failure(IMPORT_FAILURE_COPY);
    } finally {
      isImporting.value = false;
    }
  }

  onScopeDispose(() => {
    generation += 1;
    stopPolling();
  });

  return {
    conversionError,
    conversionMessage,
    conversionStatus,
    importDocument,
    isConverting,
    isImporting,
    retryConversionStatus,
  };
}
