/**
 * Exam workspace AI answer-key suggestions.
 *
 * Domain purpose:
 *   Request AI suggestions for the questions exactly as the editor shows
 *   them — every keyless keyed question, or one named question — poll the
 *   job until it settles, and write each arriving suggestion onto its
 *   question through the document owner. Requests work with unsaved
 *   changes because the editor's current document is what gets sent.
 *
 * Relationships:
 *   - Used by `ExamWorkspaceView` next to `useExamWorkspaceDocument`.
 *   - Delegates transport to `api/examWorkspace.ts`.
 */

import { computed, onScopeDispose, ref, watch } from "vue";
import type { Ref } from "vue";

import {
  getExamWorkspaceAnswerKeySuggestions,
  requestExamWorkspaceAnswerKeySuggestions,
} from "../../../api/examWorkspace";
import type {
  ExamWorkspaceAnswerKeySuggestionItem,
  ExamWorkspaceAnswerKeySuggestionsStatus,
  ExamWorkspaceDocumentSummary,
  NativeExamDocument,
} from "../../../api/examWorkspace";
import { useToast } from "../../../composables/useToast";

export const EXAM_WORKSPACE_ENRICHMENT_POLL_MS = 3000;
export const EXAM_WORKSPACE_ENRICHMENT_MAX_POLL_MS = 30_000;

const REQUEST_FAILURE_COPY = "Det gick inte att begära facitförslag. Försök igen.";
const STATUS_FAILURE_COPY = "Det gick inte att hämta facitförslagen. Försök igen.";
const NO_SUGGESTIONS_COPY = "Inga facitförslag kom tillbaka. Komplettera facit manuellt.";

function isPending(status: ExamWorkspaceAnswerKeySuggestionsStatus | null): boolean {
  return status?.state === "queued" || status?.state === "running";
}

export function useExamWorkspaceEnrichment(
  summary: Ref<ExamWorkspaceDocumentSummary | null>,
  document: Ref<NativeExamDocument | null>,
  applySuggestions: (suggestions: ExamWorkspaceAnswerKeySuggestionItem[]) => void,
) {
  const toast = useToast();

  const enrichmentStatus = ref<ExamWorkspaceAnswerKeySuggestionsStatus | null>(null);
  const isRequesting = ref(false);
  let pollTimer: ReturnType<typeof setTimeout> | null = null;
  let generation = 0;
  // Consecutive failed status polls. The first failure of a streak shows the
  // toast; each further failure doubles the retry delay up to the cap.
  let pollFailures = 0;

  const isEnrichmentPending = computed(() => isPending(enrichmentStatus.value));

  const enrichmentMessage = computed<string | null>(() => {
    const status = enrichmentStatus.value;
    if (!status) {
      return null;
    }
    switch (status.state) {
      case "queued":
        return "Facitförslagen väntar på tur.";
      case "running":
        return "Facitförslagen tas fram …";
      case "succeeded":
        return status.suggestions.length > 0
          ? `${status.suggestions.length} facitförslag har lagts in på frågorna.`
          : NO_SUGGESTIONS_COPY;
      case "not_eligible":
      case "failed":
        return status.message ?? REQUEST_FAILURE_COPY;
      default:
        return null;
    }
  });

  function stopPolling(): void {
    if (pollTimer !== null) {
      clearTimeout(pollTimer);
      pollTimer = null;
    }
  }

  function pollDelayMs(): number {
    const backoff = 2 ** Math.max(0, pollFailures - 1);
    return Math.min(
      EXAM_WORKSPACE_ENRICHMENT_POLL_MS * backoff,
      EXAM_WORKSPACE_ENRICHMENT_MAX_POLL_MS,
    );
  }

  function schedulePoll(lineageId: string, jobId: string, pollGeneration: number): void {
    stopPolling();
    pollTimer = setTimeout(() => {
      pollTimer = null;
      void refreshStatus(lineageId, jobId, pollGeneration);
    }, pollDelayMs());
  }

  function applyStatus(
    lineageId: string,
    pollGeneration: number,
    status: ExamWorkspaceAnswerKeySuggestionsStatus,
  ): void {
    if (pollGeneration !== generation) {
      return;
    }
    pollFailures = 0;
    enrichmentStatus.value = status;
    if (status.state === "succeeded" && status.suggestions.length > 0) {
      applySuggestions([...status.suggestions]);
    }
    if (isPending(status) && status.job_id) {
      schedulePoll(lineageId, status.job_id, pollGeneration);
    }
  }

  async function refreshStatus(
    lineageId: string,
    jobId: string,
    pollGeneration: number,
  ): Promise<void> {
    try {
      const status = await getExamWorkspaceAnswerKeySuggestions(lineageId, jobId);
      applyStatus(lineageId, pollGeneration, status);
    } catch {
      if (pollGeneration !== generation) {
        return;
      }
      if (pollFailures === 0) {
        toast.failure(STATUS_FAILURE_COPY);
      }
      pollFailures += 1;
      if (isPending(enrichmentStatus.value)) {
        schedulePoll(lineageId, jobId, pollGeneration);
      }
    }
  }

  async function requestSuggestions(itemId?: string): Promise<void> {
    const currentSummary = summary.value;
    const currentDocument = document.value;
    if (!currentSummary || !currentDocument || isRequesting.value || isEnrichmentPending.value) {
      return;
    }
    const pollGeneration = generation;
    isRequesting.value = true;
    pollFailures = 0;
    try {
      const status = await requestExamWorkspaceAnswerKeySuggestions(
        currentSummary.lineage_id,
        currentDocument,
        itemId,
      );
      applyStatus(currentSummary.lineage_id, pollGeneration, status);
    } catch {
      toast.failure(REQUEST_FAILURE_COPY);
    } finally {
      isRequesting.value = false;
    }
  }

  function requestSuggestionsForAll(): Promise<void> {
    return requestSuggestions();
  }

  function requestSuggestionForItem(itemId: string): Promise<void> {
    return requestSuggestions(itemId);
  }

  watch(
    () => summary.value?.lineage_id ?? null,
    (lineageId, previousLineageId) => {
      if (lineageId === previousLineageId) {
        return;
      }
      generation += 1;
      stopPolling();
      pollFailures = 0;
      enrichmentStatus.value = null;
    },
  );

  onScopeDispose(stopPolling);

  return {
    enrichmentMessage,
    enrichmentStatus,
    isEnrichmentPending,
    isRequesting,
    requestSuggestionForItem,
    requestSuggestionsForAll,
  };
}
