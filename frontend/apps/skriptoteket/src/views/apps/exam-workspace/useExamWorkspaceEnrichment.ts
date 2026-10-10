/**
 * Exam workspace advisory answer-key proposals.
 *
 * Domain purpose:
 *   Request machine answer-key proposals for the saved head revision, poll
 *   the job until it settles, and expose each proposal as editor prefill.
 *   Proposals are advisory: nothing here changes the document. The teacher
 *   moves a proposal into the editor, then approves or edits it there.
 *
 * Relationships:
 *   - Used by `ExamWorkspaceView` next to `useExamWorkspaceDocument`.
 *   - Delegates transport to `api/examWorkspace.ts`.
 */

import { computed, onScopeDispose, ref, watch } from "vue";
import type { Ref } from "vue";

import {
  getExamWorkspaceEnrichment,
  startExamWorkspaceEnrichment,
} from "../../../api/examWorkspace";
import type {
  ExamWorkspaceAnswerKeyProposal,
  ExamWorkspaceDocumentSummary,
  ExamWorkspaceEnrichmentStatus,
} from "../../../api/examWorkspace";
import { useToast } from "../../../composables/useToast";

export const EXAM_WORKSPACE_ENRICHMENT_POLL_MS = 3000;

const REQUEST_FAILURE_COPY = "Det gick inte att begära facitförslag. Försök igen.";
const STATUS_FAILURE_COPY = "Det gick inte att hämta facitförslagen. Försök igen.";
const NO_PROPOSALS_COPY = "Inga facitförslag kom tillbaka. Komplettera facit manuellt.";

function isPending(status: ExamWorkspaceEnrichmentStatus | null): boolean {
  return status?.state === "queued" || status?.state === "running";
}

export function useExamWorkspaceEnrichment(
  summary: Ref<ExamWorkspaceDocumentSummary | null>,
) {
  const toast = useToast();

  const enrichmentStatus = ref<ExamWorkspaceEnrichmentStatus | null>(null);
  const isRequesting = ref(false);
  const dismissedItemIds = ref<string[]>([]);
  let pollTimer: ReturnType<typeof setTimeout> | null = null;
  let generation = 0;

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
        return status.proposals.length > 0
          ? `${status.proposals.length} facitförslag att granska.`
          : NO_PROPOSALS_COPY;
      case "not_eligible":
      case "failed":
        return status.message ?? REQUEST_FAILURE_COPY;
      default:
        return null;
    }
  });

  const openProposals = computed<ExamWorkspaceAnswerKeyProposal[]>(() => {
    const status = enrichmentStatus.value;
    if (status?.state !== "succeeded") {
      return [];
    }
    return status.proposals.filter(
      (proposal) => !dismissedItemIds.value.includes(proposal.item_id),
    );
  });

  function proposalForItem(itemId: string): ExamWorkspaceAnswerKeyProposal | null {
    return openProposals.value.find((proposal) => proposal.item_id === itemId) ?? null;
  }

  function dismissProposal(itemId: string): void {
    if (!dismissedItemIds.value.includes(itemId)) {
      dismissedItemIds.value = [...dismissedItemIds.value, itemId];
    }
  }

  function stopPolling(): void {
    if (pollTimer !== null) {
      clearTimeout(pollTimer);
      pollTimer = null;
    }
  }

  function schedulePoll(lineageId: string, pollGeneration: number): void {
    stopPolling();
    pollTimer = setTimeout(() => {
      pollTimer = null;
      void refreshStatus(lineageId, pollGeneration);
    }, EXAM_WORKSPACE_ENRICHMENT_POLL_MS);
  }

  function applyStatus(
    lineageId: string,
    pollGeneration: number,
    status: ExamWorkspaceEnrichmentStatus,
  ): void {
    if (pollGeneration !== generation) {
      return;
    }
    enrichmentStatus.value = status;
    if (isPending(status)) {
      schedulePoll(lineageId, pollGeneration);
    }
  }

  async function refreshStatus(lineageId: string, pollGeneration: number): Promise<void> {
    try {
      const status = await getExamWorkspaceEnrichment(lineageId);
      applyStatus(lineageId, pollGeneration, status);
    } catch {
      if (pollGeneration === generation) {
        toast.failure(STATUS_FAILURE_COPY);
      }
    }
  }

  async function requestProposals(): Promise<void> {
    const currentSummary = summary.value;
    if (!currentSummary || isRequesting.value || isEnrichmentPending.value) {
      return;
    }
    const pollGeneration = generation;
    isRequesting.value = true;
    try {
      const status = await startExamWorkspaceEnrichment(currentSummary.lineage_id);
      applyStatus(currentSummary.lineage_id, pollGeneration, status);
    } catch {
      toast.failure(REQUEST_FAILURE_COPY);
    } finally {
      isRequesting.value = false;
    }
  }

  watch(
    () => [summary.value?.lineage_id, summary.value?.version] as const,
    ([lineageId]) => {
      generation += 1;
      stopPolling();
      enrichmentStatus.value = null;
      dismissedItemIds.value = [];
      if (lineageId) {
        void refreshStatus(lineageId, generation);
      }
    },
  );

  onScopeDispose(stopPolling);

  return {
    dismissProposal,
    enrichmentMessage,
    enrichmentStatus,
    isEnrichmentPending,
    isRequesting,
    openProposals,
    proposalForItem,
    requestProposals,
  };
}
