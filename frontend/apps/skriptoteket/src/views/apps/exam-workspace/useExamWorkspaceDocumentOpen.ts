/**
 * Exam workspace document open lifecycle.
 *
 * Domain purpose:
 *   Open the exam for a route request's token: hold the token while reading
 *   so a retired open stops blocking at once, install while current,
 *   supersede while retired without touching state or toasting, and fail on a
 *   current failure after toasting as today. A save, rename or retry in flight
 *   refuses an open; another open never does. The rename ordering is captured
 *   before the GET so a completed rename stays reconciled in the response.
 *
 * Relationships:
 *   - Used by `useExamWorkspaceDocument`, which hands over its store, fence
 *     check, install call, selection reset, rename reconciliation and the
 *     busy and invalidation callbacks.
 *   - Transport through the exam workspace store's shared document read.
 *   - Installs through the document's `applyResponse`; keying invalidation
 *     runs through the `invalidateCopy` callback.
 */

import { computed, shallowRef } from "vue";
import type { Ref } from "vue";

import { isApiError } from "../../../api/client";
import type {
  ExamWorkspaceDocumentResponse,
  ExamWorkspaceDocumentSummary,
} from "../../../api/examWorkspace";
import { useToast } from "../../../composables/useToast";
import type { ExamWorkspaceStore } from "./examWorkspaceStore";
import type { FenceToken } from "./examWorkspaceSyncFence";
import type { ExamWorkspaceRouteOpenOutcome } from "./examWorkspaceReplacementTypes";

export const OPEN_FAILURE_COPY = "Det gick inte att öppna provet. Försök igen.";
const OPEN_OUTDATED_COPY = "Provet är sparat i ett äldre format och kan inte öppnas. Importera originalfilen på nytt.";

export type ExamWorkspaceDocumentOpenDeps = {
  /** Install the fresh response; runs only while the token is current. */
  applyResponse: (token: FenceToken, response: ExamWorkspaceDocumentResponse) => void;
  /** Record the installed cursor as the gate's own before installing, so the
   * history watcher consumes it instead of reporting it back as foreign. */
  noteInstallingCursor: (lineageId: string, cursor: string) => void;
  /** Capture rename ordering before the GET; reconciled in the read continuation. */
  beginSummaryRead: () => (summary: ExamWorkspaceDocumentSummary) => ExamWorkspaceDocumentSummary;
  /** True while the token's generation is still current. */
  isCurrent: (token: FenceToken) => boolean;
  /** A save, rename, retry, import or conversion holds the document excluding an open read. */
  isBlocked: () => boolean;
  /** Drop in-flight keying replies for the copy the install replaced. */
  invalidateCopy: () => void;
  /** The selected question; an installed open clears it. */
  selectedItemId: Ref<string | null>;
  /** The store the document read runs through. */
  store: ExamWorkspaceStore;
};

export function useExamWorkspaceDocumentOpen(deps: ExamWorkspaceDocumentOpenDeps) {
  const toast = useToast();
  /** The current request's open is still reading; a retired open stops blocking at once. */
  const openingToken = shallowRef<FenceToken | null>(null);
  /** True while the held open token is still current; the fence generation is reactive, so a retire releases this. */
  const isOpenReading = computed(() => openingToken.value !== null && deps.isCurrent(openingToken.value));

  /**
   * Capture rename ordering before the GET and reconcile in its caller's continuation.
   * Installing an opening must not wait an extra microtask: other completions
   * settling in the same turn must already see that the previous opening ended.
   */
  function beginDocumentRead() {
    const reconcile = deps.beginSummaryRead();
    return (response: ExamWorkspaceDocumentResponse): ExamWorkspaceDocumentResponse => ({
      ...response,
      summary: reconcile(response.summary),
    });
  }

  /**
   * Open the exam for the request's token: install while current, supersede
   * while retired without touching state or toasting, fail on a current
   * failure after toasting as today. A save, rename or retry in flight
   * refuses an open; another open never does. The open holds its token while
   * reading, so a retired open stops blocking and a completion clears only
   * its own token.
   */
  async function openDocument(lineageId: string, token: FenceToken): Promise<ExamWorkspaceRouteOpenOutcome> {
    if (!deps.isCurrent(token)) {
      return "superseded";
    }
    if (deps.isBlocked() && !isOpenReading.value) {
      return "failed";
    }
    openingToken.value = token;
    try {
      const reconcile = beginDocumentRead();
      const response = reconcile(await deps.store.shared.getExamWorkspaceDocument(lineageId));
      if (!deps.isCurrent(token)) {
        return "superseded";
      }
      deps.noteInstallingCursor(lineageId, response.history_cursor);
      deps.selectedItemId.value = null;
      deps.applyResponse(token, response);
      deps.invalidateCopy();
      return "installed";
    } catch (error) {
      const current = deps.isCurrent(token);
      if (current) {
        toast.failure(
          isApiError(error) && error.code === "DOCUMENT_SCHEMA_OUTDATED"
            ? OPEN_OUTDATED_COPY
            : OPEN_FAILURE_COPY,
        );
      }
      return current ? "failed" : "superseded";
    } finally {
      if (openingToken.value === token) {
        openingToken.value = null;
      }
    }
  }

  return { beginDocumentRead, isOpenReading, openDocument };
}
