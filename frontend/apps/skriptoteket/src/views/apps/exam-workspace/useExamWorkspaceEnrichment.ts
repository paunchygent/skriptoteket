/**
 * Exam workspace AI answer-key suggestions.
 *
 * Domain purpose:
 *   Request AI suggestions for the questions exactly as the editor shows
 *   them — every keyless keyed question, or one named question — poll the
 *   job until it settles, and write each arriving suggestion onto its
 *   question through the document owner. Requests work with unsaved
 *   changes because the editor's current document is what gets sent. A job
 *   belongs to the exam opening it was requested in: its results, status,
 *   failure toast and next poll take effect only while that opening is still
 *   open, checked when each completion lands. Each new opening asks the
 *   server for the newest job requested on its saved version, so a job this
 *   page lost (reload, reopen, switching back) is polled or delivered as if
 *   this opening had requested it (TASK-SKRIPT-39-04-09 P1, P2, P7). A failed
 *   lookup is shown with a retry that asks again, while that opening is open.
 *
 * Relationships:
 *   - Used by `ExamWorkspaceView` next to `useExamWorkspaceDocument`.
 *   - Delegates transport to the exam workspace store's teacher services.
 *   - Reads the open exam opening from `useExamWorkspaceDocument`.
 */

import { computed, onScopeDispose, shallowRef, watch } from "vue";
import type { Ref } from "vue";

import type {
  ExamWorkspaceAnswerKeySuggestionItem,
  ExamWorkspaceAnswerKeySuggestionsStatus,
  NativeExamDocument,
} from "../../../api/examWorkspace";
import { useAiAccess } from "../../../composables/useAiAccess";
import { useToast } from "../../../composables/useToast";
import {
  aiLimitFromError,
  aiLimitFromStatus,
  aiTryAgainFromError,
  markAiDailyLimit,
} from "../../../composables/aiDailyLimit";
import type { ExamWorkspaceTeacherServices } from "./examWorkspaceStore";
import type { ExamWorkspaceOpening } from "./useExamWorkspaceDocument";

export const EXAM_WORKSPACE_ENRICHMENT_POLL_MS = 3000;
export const EXAM_WORKSPACE_ENRICHMENT_MAX_POLL_MS = 30_000;

const REQUEST_FAILURE_COPY = "Det gick inte att begära facitförslag. Försök igen.";
const STATUS_FAILURE_COPY = "Det gick inte att hämta facitförslagen. Försök igen.";
const NO_SUGGESTIONS_COPY = "Inga facitförslag kom tillbaka. Komplettera facit manuellt.";
const LOOKUP_FAILURE_COPY = "Kunde inte hämta väntande facitförslag.";

function isPending(status: ExamWorkspaceAnswerKeySuggestionsStatus | null): boolean {
  return status?.state === "queued" || status?.state === "running";
}

export type ExamWorkspaceEnrichmentBinding = {
  /** The exam opening in front of the teacher. */
  openExam: Readonly<Ref<ExamWorkspaceOpening | null>>;
  document: Readonly<Ref<NativeExamDocument | null>>;
  /** The saved version the open copy stands on. */
  savedRevision: Readonly<Ref<number | null>>;
  isOpen: (opening: ExamWorkspaceOpening) => boolean;
  applySuggestions: (
    opening: ExamWorkspaceOpening,
    suggestions: ExamWorkspaceAnswerKeySuggestionItem[],
  ) => void;
  /** The teacher services the suggestion requests and polls run through; null in guest mode. */
  teacher: ExamWorkspaceTeacherServices | null;
};

type Job = { opening: ExamWorkspaceOpening; status: ExamWorkspaceAnswerKeySuggestionsStatus };

export function useExamWorkspaceEnrichment(binding: ExamWorkspaceEnrichmentBinding) {
  const toast = useToast();
  // The paid answer-key request is admin-only until the spend cap ships (TASK-SKRIPT-REP-0044 L3).
  const { canUseAi } = useAiAccess();

  const job = shallowRef<Job | null>(null);
  const requestingIn = shallowRef<ExamWorkspaceOpening | null>(null);
  // The opening whose lost-job lookup failed and has not been asked again.
  const lookupFailedIn = shallowRef<ExamWorkspaceOpening | null>(null);
  let pollTimer: ReturnType<typeof setTimeout> | null = null;
  let disposed = false;
  // Consecutive failed status polls. The first failure of a streak shows the
  // toast; each further failure doubles the retry delay up to the cap.
  let pollFailures = 0;

  /** Whether a completion requested in `opening` may still take effect. */
  function isLive(opening: ExamWorkspaceOpening): boolean {
    return !disposed && binding.isOpen(opening);
  }

  // Status and request state of another exam's opening are not this exam's.
  const enrichmentStatus = computed<ExamWorkspaceAnswerKeySuggestionsStatus | null>(() => {
    const current = job.value;
    return current && isLive(current.opening) ? current.status : null;
  });
  const isRequesting = computed(() => {
    const opening = requestingIn.value;
    return opening !== null && isLive(opening);
  });
  const isEnrichmentPending = computed(() => isPending(enrichmentStatus.value));
  const enrichmentLookupError = computed<string | null>(() => {
    const opening = lookupFailedIn.value;
    return opening && isLive(opening) ? LOOKUP_FAILURE_COPY : null;
  });

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

  function schedulePoll(opening: ExamWorkspaceOpening, jobId: string): void {
    stopPolling();
    pollTimer = setTimeout(() => {
      pollTimer = null;
      void refreshStatus(opening, jobId);
    }, pollDelayMs());
  }

  function applyStatus(
    opening: ExamWorkspaceOpening,
    status: ExamWorkspaceAnswerKeySuggestionsStatus,
  ): void {
    if (!isLive(opening)) {
      return;
    }
    // The door's daily limit is terminal for the page session: the status
    // message already says so, and the AI controls disable on the flag.
    const limit = aiLimitFromStatus(status);
    if (limit !== null) {
      markAiDailyLimit(limit);
    }
    pollFailures = 0;
    job.value = { opening, status };
    // A failed job still delivers the suggestions it produced before the
    // failure; its message above stays the failure message.
    if (
      (status.state === "succeeded" || status.state === "failed") &&
      status.suggestions.length > 0
    ) {
      binding.applySuggestions(opening, [...status.suggestions]);
    }
    if (isPending(status) && status.job_id) {
      schedulePoll(opening, status.job_id);
    }
  }

  async function refreshStatus(opening: ExamWorkspaceOpening, jobId: string): Promise<void> {
    const teacher = binding.teacher;
    if (!isLive(opening) || !teacher) {
      return;
    }
    try {
      const status = await teacher.getExamWorkspaceAnswerKeySuggestions(opening.lineageId, jobId);
      applyStatus(opening, status);
    } catch (error) {
      if (!isLive(opening)) {
        return;
      }
      // No toast for the door's limit: the flag disables the AI controls.
      const limit = aiLimitFromError(error);
      if (limit !== null) {
        markAiDailyLimit(limit);
        return;
      }
      if (pollFailures === 0) {
        toast.failure(aiTryAgainFromError(error) ?? STATUS_FAILURE_COPY);
      }
      pollFailures += 1;
      if (isPending(enrichmentStatus.value)) {
        schedulePoll(opening, jobId);
      }
    }
  }

  async function requestSuggestions(itemId?: string): Promise<void> {
    const opening = binding.openExam.value;
    const currentDocument = binding.document.value;
    const teacher = binding.teacher;
    if (
      !canUseAi.value ||
      !opening ||
      !currentDocument ||
      !teacher ||
      isRequesting.value ||
      isEnrichmentPending.value
    ) {
      return;
    }
    requestingIn.value = opening;
    lookupFailedIn.value = null;
    pollFailures = 0;
    try {
      const status = await teacher.requestExamWorkspaceAnswerKeySuggestions(
        opening.lineageId,
        currentDocument,
        itemId,
      );
      applyStatus(opening, status);
    } catch (error) {
      if (!isLive(opening)) {
        return;
      }
      const requestLimit = aiLimitFromError(error);
      if (requestLimit !== null) {
        markAiDailyLimit(requestLimit);
        return;
      }
      toast.failure(aiTryAgainFromError(error) ?? REQUEST_FAILURE_COPY);
    } finally {
      if (requestingIn.value === opening) {
        requestingIn.value = null;
      }
    }
  }

  /**
   * Find the job this opening's exam has on its saved version. Admitted only
   * if, when the answer lands, the opening is still open, its copy still
   * stands on the asked-for saved version (an older version's job never
   * applies), and the teacher has not started a job of their own here. A
   * failure is shown under the same conditions, minus the version check.
   */
  async function resumeLostJob(opening: ExamWorkspaceOpening): Promise<void> {
    const teacher = binding.teacher;
    const revision = binding.savedRevision.value;
    if (!teacher || revision === null) {
      return;
    }
    const ownJobStarted = () => job.value?.opening === opening || requestingIn.value === opening;
    let status: ExamWorkspaceAnswerKeySuggestionsStatus | null;
    try {
      status = await teacher.findExamWorkspaceAnswerKeySuggestions(opening.lineageId, revision);
    } catch (error) {
      const lookupLimit = aiLimitFromError(error);
      if (lookupLimit !== null) {
        markAiDailyLimit(lookupLimit);
        return;
      }
      if (isLive(opening) && !ownJobStarted()) {
        lookupFailedIn.value = opening;
        toast.failure(aiTryAgainFromError(error) ?? LOOKUP_FAILURE_COPY);
      }
      return;
    }
    if (!status || binding.savedRevision.value !== revision || ownJobStarted()) {
      return;
    }
    // Like every completion, it takes effect only while `opening` is open.
    applyStatus(opening, status);
  }

  // Only triggers the lookup; whether its answer applies is decided when it lands.
  watch(binding.openExam, (opening) => {
    if (opening) {
      void resumeLostJob(opening);
    }
  });

  /** Ask again for the job whose lookup failed in the opening still open. */
  async function retryEnrichmentLookup(): Promise<void> {
    const opening = lookupFailedIn.value;
    if (!opening || !isLive(opening)) {
      return;
    }
    lookupFailedIn.value = null;
    await resumeLostJob(opening);
  }

  function requestSuggestionsForAll(): Promise<void> {
    return requestSuggestions();
  }

  function requestSuggestionForItem(itemId: string): Promise<void> {
    return requestSuggestions(itemId);
  }

  // Disposal ends every outstanding request and poll: a late completion or
  // failure must not apply results, toast, or schedule a new poll for a view
  // that no longer exists.
  onScopeDispose(() => {
    disposed = true;
    stopPolling();
  });

  return {
    enrichmentLookupError,
    enrichmentMessage,
    enrichmentStatus,
    isEnrichmentPending,
    isRequesting,
    requestSuggestionForItem,
    requestSuggestionsForAll,
    retryEnrichmentLookup,
  };
}
